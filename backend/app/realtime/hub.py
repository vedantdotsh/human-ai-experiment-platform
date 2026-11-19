import asyncio
from uuid import UUID

from fastapi import WebSocket


class Connection:
    """One browser socket. Outgoing messages go through a queue drained by a
    writer task, so state changes can enqueue while holding a lock without ever
    waiting on the network, and every connection sees messages in order."""

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self._queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        self._writer = asyncio.create_task(self._drain())

    def enqueue(self, message: dict) -> None:
        self._queue.put_nowait(("send", message))

    def close(self, code: int) -> None:
        self._queue.put_nowait(("close", code))

    async def _drain(self) -> None:
        try:
            while True:
                kind, payload = await self._queue.get()
                if kind == "send":
                    await self.ws.send_json(payload)
                else:
                    await self.ws.close(code=payload)  # type: ignore[arg-type]
                    return
        except Exception:
            return  # socket already gone; the receive loop notices and cleans up

    def stop(self) -> None:
        self._writer.cancel()


class Hub:
    """Registry of live sockets per run and participant. Memory only."""

    def __init__(self) -> None:
        self._conns: dict[UUID, dict[UUID, set[Connection]]] = {}

    def add(self, session_id: UUID, participant_id: UUID, conn: Connection) -> None:
        self._conns.setdefault(session_id, {}).setdefault(participant_id, set()).add(conn)

    def remove(
        self, session_id: UUID, participant_id: UUID, conn: Connection
    ) -> tuple[bool, bool]:
        """Returns (was_registered, was_last_socket_for_participant)."""
        conns = self._conns.get(session_id, {}).get(participant_id)
        if not conns or conn not in conns:
            return False, False
        conns.discard(conn)
        if not conns:
            del self._conns[session_id][participant_id]
            return True, True
        return True, False

    def connected(self, session_id: UUID) -> set[UUID]:
        return set(self._conns.get(session_id, {}))

    def send(self, session_id: UUID, participant_id: UUID, message: dict) -> None:
        for conn in self._conns.get(session_id, {}).get(participant_id, ()):
            conn.enqueue(message)

    def broadcast(self, session_id: UUID, message: dict) -> None:
        for conns in self._conns.get(session_id, {}).values():
            for conn in conns:
                conn.enqueue(message)

    def drop_participant(self, session_id: UUID, participant_id: UUID, code: int) -> None:
        """Unregister and close every socket of a participant whose seat is gone."""
        for conn in self._conns.get(session_id, {}).pop(participant_id, set()):
            conn.close(code)
