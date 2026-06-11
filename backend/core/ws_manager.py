from typing import Dict
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, ws: WebSocket):
        # 移除这行，因为在 ws_api.py 中已经接受了连接
        # await ws.accept()
        self._connections[device_id] = ws

    def disconnect(self, device_id: str):
        self._connections.pop(device_id, None)

    def is_device_online(self, device_id: str) -> bool:
        return device_id in self._connections

    async def send_to_device(self, device_id: str, message: str) -> bool:
        ws = self._connections.get(device_id)
        if ws:
            await ws.send_text(message)
            return True
        return False
