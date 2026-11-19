from psycopg_pool import AsyncConnectionPool

from app.event_log.store import append_event

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    config JSONB NOT NULL,
    phase TEXT NOT NULL,
    phase_seq INTEGER NOT NULL DEFAULT 0,
    phase_started_at TIMESTAMPTZ NOT NULL,
    phase_deadline TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('waiting', 'running', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    winner_slot SMALLINT CHECK (winner_slot BETWEEN 1 AND 3)
);

CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (id),
    slot SMALLINT NOT NULL CHECK (slot BETWEEN 1 AND 3),
    role TEXT NOT NULL CHECK (role IN ('human', 'ai')),
    claim_state TEXT NOT NULL CHECK (claim_state IN ('open', 'claimed')),
    UNIQUE (session_id, slot)
);

CREATE TABLE IF NOT EXISTS experiment_events (
    session_id UUID NOT NULL REFERENCES sessions (id),
    seq INTEGER NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    phase_seq INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('message', 'vote', 'phase_change', 'join', 'disconnect')
    ),
    actor_id UUID REFERENCES participants (id),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (session_id, seq)
);
"""


async def init_schema(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        await conn.execute(SCHEMA)


async def abandon_unfinished_runs(pool: AsyncConnectionPool) -> int:
    """Mark runs left over from a previous backend process as abandoned."""
    async with pool.connection() as conn, conn.transaction():
        cur = await conn.execute(
            """
            UPDATE sessions
               SET status = 'abandoned', phase = 'abandoned',
                   phase_seq = phase_seq + 1, phase_started_at = clock_timestamp(),
                   phase_deadline = NULL
             WHERE status IN ('waiting', 'running')
         RETURNING id
            """
        )
        rows = await cur.fetchall()
        for row in rows:
            await append_event(
                conn,
                row["id"],
                "phase_change",
                payload={"phase": "abandoned", "reason": "backend_restart"},
            )
        return len(rows)

