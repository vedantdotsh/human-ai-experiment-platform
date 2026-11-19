import asyncio
import logging
import random
import time
from dataclasses import dataclass
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from app.ai import prompts
from app.ai.provider import MistralProvider, ProviderError
from app.ai.scripted import ASKS_ABOUT_TYPE, fallback_ballot, pick_line
from app.ai.validation import clean_chat, parse_vote
from app.experiment.errors import Rejected
from app.experiment.phases import LABELS, duration_seconds, phase_at
from app.messaging.service import MessageService
from app.session.config import Config
from app.voting.service import ballot_totals, labelled
from app.voting.service import VoteService

log = logging.getLogger("ai.players")


@dataclass(frozen=True)
class AiSeat:
    participant_id: UUID
    label: str


@dataclass
class Context:
    messages: list[tuple[str, str]]  # (author label, text), oldest first
    vote1_totals: dict[str, int] | None


class AiPlayers:
    """Plays the AI seats. Each AI speaks two or three times per discussion and votes
    once per round, at randomized times inside the phase. Actions go through the same
    MessageService and VoteService as humans, so they are validated, persisted and
    broadcast identically, and anything late is rejected there."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        config: Config,
        messages: MessageService,
        votes: VoteService,
        provider: MistralProvider | None,
    ) -> None:
        self._pool = pool
        self._config = config
        self._messages = messages
        self._votes = votes
        self._provider = provider
        self._rng = random.SystemRandom()
        self._tasks: dict[UUID, list[asyncio.Task]] = {}
        self._used_lines: dict[UUID, set[str]] = {}

    # --- scheduling -----------------------------------------------------------

    def phase_started(self, session_id: UUID, phase_seq: int, deadline: float | None) -> None:
        for task in self._tasks.pop(session_id, []):
            task.cancel()
        phase, round_number = phase_at(phase_seq)
        if phase == "results":
            self._used_lines.pop(session_id, None)
        if phase not in ("discussion", "voting") or deadline is None:
            return
        duration = duration_seconds(phase, self._config) or 0
        self._tasks[session_id] = [
            asyncio.create_task(
                self._plan(session_id, phase_seq, phase, round_number or 0, deadline - duration, deadline)
            )
        ]

    async def _plan(
        self, session_id: UUID, phase_seq: int, phase: str, round_number: int, start: float, deadline: float
    ) -> None:
        try:
            seats = await self._ai_seats(session_id)
            tasks = self._tasks.get(session_id)
            if tasks is None:
                return
            for seat in seats:
                run = self._discuss if phase == "discussion" else self._vote
                tasks.append(
                    asyncio.create_task(run(session_id, seat, phase_seq, round_number, start, deadline))
                )
        except Exception:
            log.exception("could not schedule AI players")

    async def _ai_seats(self, session_id: UUID) -> list[AiSeat]:
        async with self._pool.connection() as c:
            cur = await c.execute(
                "SELECT id, slot FROM participants WHERE session_id = %s AND role = 'ai' ORDER BY slot",
                (session_id,),
            )
            return [AiSeat(r["id"], LABELS[r["slot"]]) for r in await cur.fetchall()]

    def _chat_offsets(self, duration: float) -> list[float]:
        """Two or three start times, one per equal slice of the usable window, so they
        are spread out but not evenly spaced."""
        count = self._rng.choice([2, 3])
        low = min(0.1 * duration + 1, 0.3 * duration)
        high = max(duration - self._config.ai_call_timeout_seconds - 5, 0.45 * duration)
        width = (high - low) / count
        return [self._rng.uniform(low + i * width, low + (i + 1) * width) for i in range(count)]

    # --- chat ---------------------------------------------------------------------

    async def _discuss(
        self, session_id: UUID, seat: AiSeat, phase_seq: int, round_number: int, start: float, deadline: float
    ) -> None:
        try:
            for offset in self._chat_offsets(deadline - start):
                await asyncio.sleep(max(0.0, start + offset - time.time()))
                await self._speak(session_id, seat, phase_seq, round_number, deadline)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("AI chat turn failed")

    async def _speak(
        self, session_id: UUID, seat: AiSeat, phase_seq: int, round_number: int, deadline: float
    ) -> None:
        context = await self._context(session_id, round_number)
        budget = min(self._config.ai_call_timeout_seconds, deadline - time.time() - 2.0)
        text, meta = await self._chat_text(session_id, seat, round_number, context, budget)
        # Looks like typing: a short think, then time proportional to the length.
        typing = self._rng.uniform(0.5, 1.5) + len(text) * self._rng.uniform(0.05, 0.10)
        if time.time() + typing > deadline - 0.3:
            log.info("AI message dropped: no time left in the phase")
            return
        await asyncio.sleep(typing)
        try:
            await self._messages.submit(
                session_id, seat.participant_id, text, phase_seq, int(time.time() * 1000), meta
            )
        except Rejected as exc:
            log.info("AI message rejected: %s", exc.reason)

    async def _chat_text(
        self, session_id: UUID, seat: AiSeat, round_number: int, context: Context, budget: float
    ) -> tuple[str, dict]:
        previous = [text for _, text in context.messages]
        # If anyone recently asked what the players are, never let the model answer:
        # a scripted deflection cannot hint at it.
        asked = next(
            (t for a, t in reversed(context.messages[-3:]) if a != seat.label and ASKS_ABOUT_TYPE.search(t)),
            None,
        )
        reason = "no_key"
        if self._provider is not None and asked is not None:
            reason = "type_question"
        elif self._provider is not None:
            reason = "no_time"
            if budget >= 1.0:
                try:
                    raw = await asyncio.wait_for(
                        self._provider.complete(
                            prompts.SYSTEM.format(own_label=seat.label),
                            prompts.CHAT.format(
                                transcript=prompts.transcript(context.messages, seat.label),
                                round_note=prompts.round_note(round_number, context.vote1_totals),
                                own_label=seat.label,
                            ),
                            max_tokens=60,
                            temperature=0.9,
                            timeout=budget,
                        ),
                        budget,
                    )
                    text, why = clean_chat(raw, previous)
                    if text:
                        return text, {"source": "llm", "model": self._provider.model}
                    reason = why
                except (TimeoutError, asyncio.TimeoutError):
                    reason = "timeout"
                except ProviderError as exc:
                    reason = exc.reason
        others = [label for label in LABELS.values() if label != seat.label]
        last_other = asked or next(
            (t for a, t in reversed(context.messages) if a != seat.label), None
        )
        used = self._used_lines.setdefault(session_id, set())
        line = pick_line(
            round_number, seat.label, others, last_other, not context.messages, used, previous, self._rng
        )
        return line, {"source": "scripted", "fallback_reason": reason}

    # --- voting -------------------------------------------------------------------

    async def _vote(
        self, session_id: UUID, seat: AiSeat, phase_seq: int, round_number: int, start: float, deadline: float
    ) -> None:
        try:
            duration = deadline - start
            await asyncio.sleep(
                max(0.0, start + self._rng.uniform(0.25 * duration, 0.75 * duration) - time.time())
            )
            context = await self._context(session_id, round_number)
            budget = min(self._config.ai_call_timeout_seconds, deadline - time.time() - 1.0)
            target, meta = await self._choose(seat, round_number, context, budget)
            await self._votes.submit(
                session_id, seat.participant_id, target, phase_seq, int(time.time() * 1000), meta
            )
        except asyncio.CancelledError:
            raise
        except Rejected as exc:
            log.info("AI ballot rejected: %s", exc.reason)
        except Exception:
            log.exception("AI vote failed")

    async def _choose(
        self, seat: AiSeat, round_number: int, context: Context, budget: float
    ) -> tuple[str, dict]:
        reason = "no_key"
        if self._provider is not None:
            reason = "no_time"
            if budget >= 1.0:
                try:
                    raw = await asyncio.wait_for(
                        self._provider.complete(
                            prompts.SYSTEM.format(own_label=seat.label),
                            prompts.VOTE.format(
                                transcript=prompts.transcript(context.messages, seat.label),
                                round_note=prompts.round_note(round_number, context.vote1_totals),
                            ),
                            max_tokens=10,
                            temperature=0.3,
                            timeout=budget,
                        ),
                        budget,
                    )
                    target = parse_vote(raw)
                    if target:
                        return target, {"source": "llm", "model": self._provider.model}
                    reason = "unusable"
                except (TimeoutError, asyncio.TimeoutError):
                    reason = "timeout"
                except ProviderError as exc:
                    reason = exc.reason
        authors = [author for author, _ in context.messages]
        return fallback_ballot(seat.label, authors, self._rng), {
            "source": "scripted",
            "fallback_reason": reason,
        }

    # --- shared -------------------------------------------------------------------

    async def _context(self, session_id: UUID, round_number: int) -> Context:
        async with self._pool.connection() as c:
            cur = await c.execute(
                """
                SELECT e.payload, p.slot FROM experiment_events e
                  JOIN participants p ON p.id = e.actor_id
                 WHERE e.session_id = %s AND e.event_type = 'message' ORDER BY e.seq
                """,
                (session_id,),
            )
            messages = [(LABELS[r["slot"]], r["payload"]["text"]) for r in await cur.fetchall()]
            vote1 = labelled(await ballot_totals(c, session_id, 1)) if round_number == 2 else None
        return Context(messages, vote1)

    async def shutdown(self) -> None:
        for tasks in self._tasks.values():
            for task in tasks:
                task.cancel()
        if self._provider is not None:
            await self._provider.close()
