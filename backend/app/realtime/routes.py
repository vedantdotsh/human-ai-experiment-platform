import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.experiment.engine import CLOSE_SEAT_GONE
from app.messaging.service import Rejected
from app.realtime.hub import Connection

log = logging.getLogger("realtime")
router = APIRouter()


@router.websocket("/api/ws")
async def participant_socket(ws: WebSocket, token: str) -> None:
    state = ws.app.state
    await ws.accept()
    info = state.seats.resolve(token)
    if info is None:
        await ws.close(code=CLOSE_SEAT_GONE)
        return
    conn = Connection(ws)
    try:
        if not await state.engine.on_connect(info, conn):
            await ws.close(code=CLOSE_SEAT_GONE)
            return
        while True:
            await dispatch(state, info, conn, await ws.receive_text())
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("socket error")
    finally:
        try:
            await state.engine.on_disconnect(info, conn)
        except Exception:
            log.exception("disconnect handling failed")


async def dispatch(state, info, conn: Connection, raw: str) -> None:
    def reject(action: str, reason: str) -> None:
        conn.enqueue({"type": "action.rejected", "action": action, "reason": reason})

    try:
        msg = json.loads(raw)
        kind = msg["type"]
    except (ValueError, KeyError, TypeError):
        return reject("unknown", "invalid_message")
    if kind != "message.send":
        return reject(str(kind), "unknown_action")
    text, expected = msg.get("text"), msg.get("expected_phase_seq")
    if not isinstance(text, str) or not isinstance(expected, int) or isinstance(expected, bool):
        return reject(kind, "invalid_message")
    try:
        await state.messages.submit(
            info.session_id, info.participant_id, text, expected, int(time.time() * 1000)
        )
    except Rejected as exc:
        reject(kind, exc.reason)
