"""
同桌即時同步 WebSocket。

連線網址: ws://host/ws/table/{table_id}?nickname=Daniel

ConnectionManager 以 TableID 為 key 維護該桌所有連線。
當有任一裝置更新購物車 / 送單 → broadcast 給同桌全員。
"""
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, table_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[table_id].add(ws)

    def disconnect(self, table_id: int, ws: WebSocket) -> None:
        self._connections[table_id].discard(ws)
        if not self._connections[table_id]:
            self._connections.pop(table_id, None)

    async def broadcast(self, table_id: int, message: dict[str, Any]) -> None:
        for ws in list(self._connections.get(table_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(table_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/table/{table_id}")
async def table_socket(
    websocket: WebSocket,
    table_id: int,
    nickname: str = Query(default="guest"),
) -> None:
    await manager.connect(table_id, websocket)
    await manager.broadcast(table_id, {"type": "JOIN", "nickname": nickname})
    try:
        while True:
            data = await websocket.receive_json()
            # 預期格式: {type: "CART_ADD"|"CART_REMOVE"|"ORDER_SUBMIT", payload: {...}}
            data.setdefault("nickname", nickname)
            await manager.broadcast(table_id, data)
    except WebSocketDisconnect:
        manager.disconnect(table_id, websocket)
        await manager.broadcast(table_id, {"type": "LEAVE", "nickname": nickname})
