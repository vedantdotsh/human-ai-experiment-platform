import asyncio
import random
import secrets
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.event_log.store import append_event
from app.session.config import Config


@dataclass(frozen=True)
class Seat:
    # Deliberately no label: while waiting, a seat's label would reveal which
    # other seats are AI. The player learns their label when play starts.
    seat_token: str
    phase: str


@dataclass(frozen=True)
class SeatInfo:
    session_id: UUID
    participant_id: UUID


class LeaveRejected(Exception):
    """The run has started, so the seat can no longer be released."""


class SeatListener(Protocol):
    def seat_claimed(self, session_id: UUID, participant_id: UUID) -> None: ...

    async def seat_released(self, session_id: UUID, participant_id: UUID) -> None: ...


class SeatService:
    """Seat claims, reclaims and releases.

    One process-level lock serializes finding or creating the next open session
    together with the claim, so simultaneous joins cannot create competing
    sessions. One lock per session serializes everything else that changes it.
    Lock order is always process lock, then session lock. Seat tokens live in
    memory only, which is why a backend restart ends unfinished runs.
    """

    def __init__(self, pool: AsyncConnectionPool, config: Config) -> None:
        self._pool = pool
        self._config = config
        self._process_lock = asyncio.Lock()
        self._session_locks: dict[UUID, asyncio.Lock] = {}
        self._tokens: dict[str, tuple[UUID, UUID]] = {}  # token -> (session, participant)
        self.listener: SeatListener | None = None

    def session_lock(self, session_id: UUID) -> asyncio.Lock:
        return self._session_locks.setdefault(session_id, asyncio.Lock())

    def resolve(self, token: str) -> SeatInfo | None:
        entry = self._tokens.get(token)
        return SeatInfo(*entry) if entry else None

    async def join(self, token: str | None) -> Seat:
        if token is not None:
            seat = await self._reclaim(token)
            if seat is not None:
                return seat
        async with self._process_lock:
            session_id = await self._find_open_session()
            if session_id is None:
                session_id = await self._create_session()
            seat, participant_id = await self._claim_seat(session_id)
            if self.listener:
                self.listener.seat_claimed(session_id, participant_id)
            return seat

    async def leave(self, token: str) -> None:
        entry = self._tokens.get(token)
        if entry is not None:
            await self.release(*entry, reason="leave", strict=True)

    async def release(
        self, session_id: UUID, participant_id: UUID, reason: str, strict: bool = False
    ) -> bool:
        """Free a waiting-room seat. Returns False when there was nothing to free.
        With strict, a seat in a started run raises LeaveRejected."""
        async with self.session_lock(session_id):
            async with self._pool.connection() as conn, conn.transaction():
                cur = await conn.execute(
                    """
                    SELECT p.claim_state, s.status
                      FROM participants p JOIN sessions s ON s.id = p.session_id
                     WHERE p.id = %s
                    """,
                    (participant_id,),
                )
                row = await cur.fetchone()
                if row is None or row["claim_state"] != "claimed":
                    self._drop_tokens(participant_id)
                    return False
                if row["status"] != "waiting":
                    if strict:
                        raise LeaveRejected
                    return False
                await conn.execute(
                    "UPDATE participants SET claim_state = 'open' WHERE id = %s",
                    (participant_id,),
                )
                await append_event(
                    conn, session_id, "disconnect", participant_id, {"reason": reason}
                )
            self._drop_tokens(participant_id)
        if self.listener:
            await self.listener.seat_released(session_id, participant_id)
        return True

    def _drop_tokens(self, participant_id: UUID) -> None:
        for token in [t for t, (_, p) in self._tokens.items() if p == participant_id]:
            del self._tokens[token]

    async def _reclaim(self, token: str) -> Seat | None:
        entry = self._tokens.get(token)
        if entry is None:
            return None
        session_id, participant_id = entry
        async with self.session_lock(session_id):
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    """
                    SELECT p.claim_state, s.status, s.phase
                      FROM participants p JOIN sessions s ON s.id = p.session_id
                     WHERE p.id = %s
                    """,
                    (participant_id,),
                )
                row = await cur.fetchone()
            if (
                row is not None
                and row["claim_state"] == "claimed"
                and row["status"] in ("waiting", "running")
            ):
                return Seat(token, row["phase"])
            self._tokens.pop(token, None)
            return None

    async def _find_open_session(self) -> UUID | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT s.id FROM sessions s
                 WHERE s.status = 'waiting'
                   AND EXISTS (SELECT 1 FROM participants p
                                WHERE p.session_id = s.id
                                  AND p.role = 'human' AND p.claim_state = 'open')
                 ORDER BY s.created_at LIMIT 1
                """
            )
            row = await cur.fetchone()
            return row["id"] if row else None

    async def _create_session(self) -> UUID:
        cfg = self._config
        roles = ["human"] * cfg.humans + ["ai"] * cfg.ai
        random.SystemRandom().shuffle(roles)
        session_id = uuid4()
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO sessions (id, config, phase, phase_seq, phase_started_at,
                                      status, created_at)
                VALUES (%s, %s, 'waiting', 0, clock_timestamp(), 'waiting', clock_timestamp())
                """,
                (session_id, Jsonb(cfg.snapshot())),
            )
            for slot, role in enumerate(roles, start=1):
                await conn.execute(
                    """
                    INSERT INTO participants (id, session_id, slot, role, claim_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (uuid4(), session_id, slot, role, "open" if role == "human" else "claimed"),
                )
            await append_event(conn, session_id, "phase_change", payload={"phase": "waiting"})
        return session_id

    async def _claim_seat(self, session_id: UUID) -> tuple[Seat, UUID]:
        async with self.session_lock(session_id):
            async with self._pool.connection() as conn, conn.transaction():
                cur = await conn.execute(
                    """
                    SELECT id, slot FROM participants
                     WHERE session_id = %s AND role = 'human' AND claim_state = 'open'
                     ORDER BY random() LIMIT 1
                    """,
                    (session_id,),
                )
                row = await cur.fetchone()
                if row is None:  # cannot happen: the process lock covers find + claim
                    raise RuntimeError("no open seat in the session chosen for joining")
                await conn.execute(
                    "UPDATE participants SET claim_state = 'claimed' WHERE id = %s",
                    (row["id"],),
                )
                await append_event(
                    conn,
                    session_id,
                    "join",
                    row["id"],
                    {"slot": row["slot"], "role": "human"},
                )
            token = secrets.token_urlsafe(32)
            self._tokens[token] = (session_id, row["id"])
            return Seat(token, "waiting"), row["id"]
