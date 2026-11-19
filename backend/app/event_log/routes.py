from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

# Internal only: the backend port is unpublished and the frontend proxy forwards
# /api alone, so this is reachable only from inside the Compose network.
router = APIRouter()


@router.get("/internal/sessions/{session_id}/events")
async def session_events(session_id: UUID, request: Request) -> list[dict]:
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("SELECT 1 FROM sessions WHERE id = %s", (session_id,))
        if await cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        cur = await conn.execute(
            """
            SELECT seq, ts, phase_seq, event_type AS type, actor_id AS actor, payload
              FROM experiment_events WHERE session_id = %s ORDER BY seq
            """,
            (session_id,),
        )
        return await cur.fetchall()
