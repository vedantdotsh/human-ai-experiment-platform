from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


async def append_event(
    conn: AsyncConnection,
    session_id: UUID,
    event_type: str,
    actor_id: UUID | None = None,
    payload: dict | None = None,
) -> tuple[int, datetime]:
    """Append the next event for a run. Call inside the caller's transaction and
    while holding that session's lock, so sequence numbers stay gap-free."""
    cur = await conn.execute(
        """
        INSERT INTO experiment_events (session_id, seq, phase_seq, event_type, actor_id, payload)
        SELECT %(sid)s,
               COALESCE((SELECT MAX(seq) FROM experiment_events WHERE session_id = %(sid)s), 0) + 1,
               (SELECT phase_seq FROM sessions WHERE id = %(sid)s),
               %(type)s, %(actor)s, %(payload)s
        RETURNING seq, ts
        """,
        {
            "sid": session_id,
            "type": event_type,
            "actor": actor_id,
            "payload": Jsonb(payload or {}),
        },
    )
    row = await cur.fetchone()
    return row["seq"], row["ts"]
