from collections.abc import Callable
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from app.event_log.store import append_event
from app.experiment.errors import Rejected
from app.experiment.phases import LABELS, SLOT_BY_LABEL, phase_at
from app.experiment.winner import SLOTS
from app.realtime.hub import Hub
from app.session.service import SeatService

SEATS_PER_RUN = 3


async def ballot_totals(conn: AsyncConnection, session_id: UUID, round_number: int) -> dict[int, int]:
    """Votes received per slot in a round. The log is the source of truth."""
    cur = await conn.execute(
        """
        SELECT (payload->>'target_slot')::int AS slot, count(*) AS n
          FROM experiment_events
         WHERE session_id = %s AND event_type = 'vote' AND (payload->>'round')::int = %s
         GROUP BY 1
        """,
        (session_id, round_number),
    )
    totals = {slot: 0 for slot in SLOTS}
    for row in await cur.fetchall():
        totals[row["slot"]] = row["n"]
    return totals


async def ballot_count(conn: AsyncConnection, session_id: UUID, round_number: int) -> int:
    cur = await conn.execute(
        """
        SELECT count(*) AS n FROM experiment_events
         WHERE session_id = %s AND event_type = 'vote' AND (payload->>'round')::int = %s
        """,
        (session_id, round_number),
    )
    return (await cur.fetchone())["n"]


async def own_ballot(
    conn: AsyncConnection, session_id: UUID, participant_id: UUID, round_number: int
) -> int | None:
    cur = await conn.execute(
        """
        SELECT (payload->>'target_slot')::int AS slot FROM experiment_events
         WHERE session_id = %s AND actor_id = %s AND event_type = 'vote'
           AND (payload->>'round')::int = %s
        """,
        (session_id, participant_id, round_number),
    )
    row = await cur.fetchone()
    return row["slot"] if row else None


def labelled(totals: dict[int, int]) -> dict[str, int]:
    return {LABELS[slot]: totals[slot] for slot in SLOTS}


class VoteService:
    """The one path for accepting ballots, for human and (later) AI voters alike.
    A ballot is final; the log holds at most one per participant per round."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        seats: SeatService,
        hub: Hub,
        on_all_voted: Callable[[UUID], None],
    ) -> None:
        self._pool = pool
        self._seats = seats
        self._hub = hub
        self._on_all_voted = on_all_voted

    async def submit(
        self,
        session_id: UUID,
        participant_id: UUID,
        target: str,
        expected_phase_seq: int,
        now_ms: int,
        meta: dict | None = None,
    ) -> None:
        target_slot = SLOT_BY_LABEL.get(target)
        if target_slot is None:
            raise Rejected("invalid_vote")
        async with self._seats.session_lock(session_id):
            async with self._pool.connection() as conn, conn.transaction():
                cur = await conn.execute(
                    """
                    SELECT s.status, s.phase, s.phase_seq, s.phase_deadline, p.claim_state
                      FROM sessions s JOIN participants p ON p.session_id = s.id
                     WHERE s.id = %s AND p.id = %s
                    """,
                    (session_id, participant_id),
                )
                row = await cur.fetchone()
                if row is None or row["claim_state"] != "claimed" or row["status"] != "running":
                    raise Rejected("not_running")
                if row["phase"] != "voting":
                    raise Rejected("voting_closed")
                if expected_phase_seq != row["phase_seq"]:
                    raise Rejected("stale_phase")
                if now_ms >= row["phase_deadline"].timestamp() * 1000:
                    raise Rejected("too_late")
                _, round_number = phase_at(row["phase_seq"])
                if await own_ballot(conn, session_id, participant_id, round_number) is not None:
                    raise Rejected("already_voted")
                try:
                    await append_event(
                        conn,
                        session_id,
                        "vote",
                        participant_id,
                        {"round": round_number, "target_slot": target_slot, **(meta or {})},
                    )
                except UniqueViolation:  # backstop for the one-ballot-per-round index
                    raise Rejected("already_voted")
                cast = await ballot_count(conn, session_id, round_number)
            self._hub.send(
                session_id,
                participant_id,
                {"type": "vote.recorded", "round": round_number, "target": LABELS[target_slot]},
            )
            self._hub.broadcast(
                session_id,
                {"type": "vote.progress", "round": round_number, "ballots_cast": cast},
            )
            if cast >= SEATS_PER_RUN:
                self._on_all_voted(session_id)
