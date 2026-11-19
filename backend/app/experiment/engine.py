import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from app.event_log.store import append_event
from app.experiment.phases import LABELS, PHASES, duration_seconds, phase_at
from app.experiment.winner import decide_winner
from app.realtime.hub import Connection, Hub
from app.session.config import Config
from app.session.service import SeatInfo, SeatService
from app.voting.service import ballot_count, ballot_totals, labelled, own_ballot

log = logging.getLogger("experiment")

CLOSE_SEAT_GONE = 4401


@dataclass
class Runtime:
    """In-memory, per-run bookkeeping that is not worth persisting."""

    grace: dict[UUID, asyncio.Task] = field(default_factory=dict)
    start_task: asyncio.Task | None = None
    runner: asyncio.Task | None = None
    lapsed: set[UUID] = field(default_factory=set)  # participants whose last socket closed
    early_close: asyncio.Event = field(default_factory=asyncio.Event)  # all ballots are in


def _ms(moment: datetime | None) -> int | None:
    return None if moment is None else int(moment.timestamp() * 1000)


class Engine:
    """Owns the waiting room, the server-side clock, and each socket's lifecycle.

    All state changes happen under the run's lock and are committed before the
    resulting messages are enqueued, still under the lock so every connection sees
    them in order. Network sends happen in each connection's writer task."""

    def __init__(
        self, pool: AsyncConnectionPool, config: Config, seats: SeatService, hub: Hub
    ) -> None:
        self._pool = pool
        self._config = config
        self._seats = seats
        self._hub = hub
        self._rt: dict[UUID, Runtime] = {}
        seats.listener = self

    def _runtime(self, session_id: UUID) -> Runtime:
        return self._rt.setdefault(session_id, Runtime())

    # --- seat events (SeatListener) -------------------------------------------

    def seat_claimed(self, session_id: UUID, participant_id: UUID) -> None:
        # A seat whose socket never arrives is released after the grace period.
        self._arm_grace(session_id, participant_id)

    async def seat_released(self, session_id: UUID, participant_id: UUID) -> None:
        runtime = self._runtime(session_id)
        runtime.lapsed.discard(participant_id)  # a later claim is a fresh join
        task = runtime.grace.pop(participant_id, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        self._hub.drop_participant(session_id, participant_id, CLOSE_SEAT_GONE)
        await self.evaluate(session_id)

    # --- socket lifecycle ----------------------------------------------------

    async def on_connect(self, info: SeatInfo, conn: Connection) -> bool:
        sid, pid = info.session_id, info.participant_id
        runtime = self._runtime(sid)
        async with self._seats.session_lock(sid):
            snapshot = await self._snapshot(sid, pid)
            if snapshot is None:
                return False
            if pid in runtime.lapsed:
                async with self._pool.connection() as c, c.transaction():
                    await append_event(c, sid, "join", pid, {"reconnect": True})
                runtime.lapsed.discard(pid)
            grace = runtime.grace.pop(pid, None)
            if grace is not None:
                grace.cancel()
            self._hub.add(sid, pid, conn)
            conn.enqueue(snapshot)  # first thing this socket receives
        await self.evaluate(sid)
        return True

    async def on_disconnect(self, info: SeatInfo, conn: Connection) -> None:
        sid, pid = info.session_id, info.participant_id
        registered, last = self._hub.remove(sid, pid, conn)
        conn.stop()
        if not registered or not last:
            return
        async with self._seats.session_lock(sid):
            async with self._pool.connection() as c, c.transaction():
                cur = await c.execute("SELECT status FROM sessions WHERE id = %s", (sid,))
                row = await cur.fetchone()
                if row is None or row["status"] not in ("waiting", "running"):
                    return
                await append_event(c, sid, "disconnect", pid, {"reason": "socket_closed"})
            self._runtime(sid).lapsed.add(pid)
            if row["status"] == "waiting":
                self._arm_grace(sid, pid)
        await self.evaluate(sid)

    # --- waiting room -----------------------------------------------------------

    def _arm_grace(self, session_id: UUID, participant_id: UUID) -> None:
        runtime = self._runtime(session_id)
        old = runtime.grace.pop(participant_id, None)
        if old is not None:
            old.cancel()
        runtime.grace[participant_id] = asyncio.create_task(
            self._grace(session_id, participant_id)
        )

    async def _grace(self, session_id: UUID, participant_id: UUID) -> None:
        await asyncio.sleep(self._config.waiting_grace_seconds)
        await self._seats.release(session_id, participant_id, reason="grace_expired")

    async def _ready(self, session_id: UUID) -> bool:
        """All human seats claimed and connected, and the run still waiting.
        Call with the session lock held."""
        async with self._pool.connection() as c:
            cur = await c.execute("SELECT status FROM sessions WHERE id = %s", (session_id,))
            row = await cur.fetchone()
            if row is None or row["status"] != "waiting":
                return False
            cur = await c.execute(
                "SELECT id, claim_state FROM participants WHERE session_id = %s AND role = 'human'",
                (session_id,),
            )
            humans = await cur.fetchall()
        connected = self._hub.connected(session_id)
        return all(h["claim_state"] == "claimed" and h["id"] in connected for h in humans)

    async def evaluate(self, session_id: UUID) -> None:
        """Start, or cancel, the randomized start delay when readiness changes."""
        runtime = self._runtime(session_id)
        async with self._seats.session_lock(session_id):
            ready = await self._ready(session_id)
            if ready and runtime.start_task is None:
                runtime.start_task = asyncio.create_task(self._delayed_start(session_id))
            elif not ready and runtime.start_task is not None:
                runtime.start_task.cancel()
                runtime.start_task = None

    async def _delayed_start(self, session_id: UUID) -> None:
        cfg = self._config
        delay = random.SystemRandom().uniform(
            cfg.start_delay_min_seconds, cfg.start_delay_max_seconds
        )
        await asyncio.sleep(delay)
        runtime = self._runtime(session_id)
        async with self._seats.session_lock(session_id):
            runtime.start_task = None
            if not await self._ready(session_id):  # recheck after the delay
                return
            deadline = await self._enter_phase(session_id, 1)
        runtime.runner = asyncio.create_task(self._run(session_id, deadline))

    # --- the clock ----------------------------------------------------------------

    def early_close(self, session_id: UUID) -> None:
        """Called when every ballot of the active round is in: end voting now."""
        self._runtime(session_id).early_close.set()

    async def _run(self, session_id: UUID, deadline: float | None) -> None:
        """Advance through the remaining phases on the server's clock, whether or
        not any browser is connected. A phase ends at its deadline, or sooner when
        voting is closed early."""
        runtime = self._runtime(session_id)
        try:
            for phase_seq in range(2, len(PHASES) + 1):
                try:
                    await asyncio.wait_for(
                        runtime.early_close.wait(), max(0.0, (deadline or 0) - time.time())
                    )
                except TimeoutError:
                    pass
                async with self._seats.session_lock(session_id):
                    deadline = await self._enter_phase(session_id, phase_seq)
                    runtime.early_close.clear()
        except Exception:
            log.exception("run %s stopped advancing", session_id)

    async def _enter_phase(self, session_id: UUID, phase_seq: int) -> float | None:
        """Commit a phase change and enqueue it. Call with the session lock held.
        Leaving round 1 voting publishes its totals; entering results decides the
        winner in the same transaction that completes the run."""
        phase, round_number = phase_at(phase_seq)
        now = time.time()
        seconds = duration_seconds(phase, self._config)
        deadline = None if seconds is None else now + seconds
        deadline_at = None if deadline is None else datetime.fromtimestamp(deadline, UTC)
        finished = phase == "results"
        payload: dict = {"phase": phase, "round": round_number, "deadline": _ms(deadline_at)}
        vote1_totals = results = None
        winner_slot = None
        async with self._pool.connection() as c, c.transaction():
            if phase_seq == 3:
                vote1_totals = await ballot_totals(c, session_id, 1)
            if finished:
                vote1 = await ballot_totals(c, session_id, 1)
                vote2 = await ballot_totals(c, session_id, 2)
                winner_slot, decided_by = decide_winner(vote1, vote2, random.SystemRandom().choice)
                results = {"winner": LABELS[winner_slot], "totals": labelled(vote2)}
                payload |= {
                    "winner_slot": winner_slot,
                    "decided_by": decided_by,
                    "vote_totals": {"round1": vote1, "round2": vote2},
                }
            await c.execute(
                """
                UPDATE sessions
                   SET phase = %s, phase_seq = %s, phase_started_at = %s,
                       phase_deadline = %s, status = %s, completed_at = %s, winner_slot = %s
                 WHERE id = %s
                """,
                (
                    phase,
                    phase_seq,
                    datetime.fromtimestamp(now, UTC),
                    deadline_at,
                    "completed" if finished else "running",
                    datetime.fromtimestamp(now, UTC) if finished else None,
                    winner_slot,
                    session_id,
                ),
            )
            await append_event(c, session_id, "phase_change", payload=payload)
        self._hub.broadcast(
            session_id,
            {
                "type": "phase.changed",
                "phase": phase,
                "round": round_number,
                "phase_seq": phase_seq,
                "server_time": int(now * 1000),
                "deadline": _ms(deadline_at),
            },
        )
        if vote1_totals is not None:
            self._hub.broadcast(
                session_id,
                {"type": "vote.summary", "round": 1, "totals": labelled(vote1_totals)},
            )
        if results is not None:
            self._hub.broadcast(session_id, {"type": "results.ready", **results})
        if phase_seq == 1:
            # Labels are revealed only now, so each socket gets a fresh snapshot.
            for participant_id in self._hub.connected(session_id):
                snapshot = await self._snapshot(session_id, participant_id)
                if snapshot is not None:
                    self._hub.send(session_id, participant_id, snapshot)
        return deadline

    # --- snapshot ---------------------------------------------------------------

    async def _snapshot(self, session_id: UUID, participant_id: UUID) -> dict | None:
        async with self._pool.connection() as c:
            cur = await c.execute(
                """
                SELECT s.phase, s.phase_seq, s.phase_deadline, s.winner_slot,
                       p.slot, p.claim_state
                  FROM sessions s JOIN participants p ON p.session_id = s.id
                 WHERE s.id = %s AND p.id = %s
                """,
                (session_id, participant_id),
            )
            row = await cur.fetchone()
            if row is None or row["claim_state"] != "claimed":
                return None
            cur = await c.execute(
                """
                SELECT e.ts, e.payload, p.slot
                  FROM experiment_events e JOIN participants p ON p.id = e.actor_id
                 WHERE e.session_id = %s AND e.event_type = 'message' ORDER BY e.seq
                """,
                (session_id,),
            )
            messages = await cur.fetchall()
            phase_seq = row["phase_seq"]
            ballots_cast = own_vote = vote1_totals = results = None
            if row["phase"] == "voting":
                round_number = phase_at(phase_seq)[1]
                ballots_cast = await ballot_count(c, session_id, round_number)
                own = await own_ballot(c, session_id, participant_id, round_number)
                own_vote = LABELS[own] if own else None
            if phase_seq >= 3:
                vote1_totals = labelled(await ballot_totals(c, session_id, 1))
            if row["phase"] == "results":
                results = {
                    "winner": LABELS[row["winner_slot"]],
                    "totals": labelled(await ballot_totals(c, session_id, 2)),
                }
        started = phase_seq >= 1
        return {
            "type": "session.snapshot",
            "phase": row["phase"],
            "round": phase_at(phase_seq)[1] if started else None,
            "phase_seq": phase_seq,
            "server_time": int(time.time() * 1000),
            "deadline": _ms(row["phase_deadline"]),
            "own_label": LABELS[row["slot"]] if started else None,
            "messages": [
                {
                    "number": number,
                    "author": LABELS[m["slot"]],
                    "round": m["payload"]["round"],
                    "text": m["payload"]["text"],
                    "ts": _ms(m["ts"]),
                }
                for number, m in enumerate(messages, start=1)
            ],
            "ballots_cast": ballots_cast,
            "own_vote": own_vote,
            "vote1_totals": vote1_totals,
            "results": results,
        }

    async def shutdown(self) -> None:
        for runtime in self._rt.values():
            for task in [runtime.start_task, runtime.runner, *runtime.grace.values()]:
                if task is not None:
                    task.cancel()
