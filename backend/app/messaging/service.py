from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from app.event_log.store import append_event
from app.experiment.errors import Rejected
from app.experiment.phases import LABELS, phase_at
from app.realtime.hub import Hub
from app.session.service import SeatService

MAX_MESSAGE_LENGTH = 500


class MessageService:
    """The one path for accepting chat, for human and (later) AI senders alike:
    validate under the session lock, persist, commit, then enqueue the broadcast."""

    def __init__(self, pool: AsyncConnectionPool, seats: SeatService, hub: Hub) -> None:
        self._pool = pool
        self._seats = seats
        self._hub = hub

    async def submit(
        self,
        session_id: UUID,
        participant_id: UUID,
        text: str,
        expected_phase_seq: int,
        now_ms: int,
    ) -> None:
        text = text.strip()
        if not text or len(text) > MAX_MESSAGE_LENGTH:
            raise Rejected("invalid_message")
        async with self._seats.session_lock(session_id):
            async with self._pool.connection() as conn, conn.transaction():
                cur = await conn.execute(
                    """
                    SELECT s.status, s.phase, s.phase_seq, s.phase_deadline,
                           p.slot, p.claim_state
                      FROM sessions s JOIN participants p ON p.session_id = s.id
                     WHERE s.id = %s AND p.id = %s
                    """,
                    (session_id, participant_id),
                )
                row = await cur.fetchone()
                if row is None or row["claim_state"] != "claimed" or row["status"] != "running":
                    raise Rejected("not_running")
                if row["phase"] != "discussion":
                    raise Rejected("chat_closed")
                if expected_phase_seq != row["phase_seq"]:
                    raise Rejected("stale_phase")
                if now_ms >= row["phase_deadline"].timestamp() * 1000:
                    raise Rejected("too_late")
                _, round_number = phase_at(row["phase_seq"])
                _, ts = await append_event(
                    conn,
                    session_id,
                    "message",
                    participant_id,
                    {"round": round_number, "text": text},
                )
                # Counts chat only, so it reveals nothing about joins or disconnects.
                cur = await conn.execute(
                    """
                    SELECT count(*) AS n FROM experiment_events
                     WHERE session_id = %s AND event_type = 'message'
                    """,
                    (session_id,),
                )
                number = (await cur.fetchone())["n"]
            self._hub.broadcast(
                session_id,
                {
                    "type": "message.created",
                    "number": number,
                    "author": LABELS[row["slot"]],
                    "round": round_number,
                    "text": text,
                    "ts": int(ts.timestamp() * 1000),
                },
            )
