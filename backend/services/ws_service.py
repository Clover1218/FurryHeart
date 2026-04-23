from fastapi import WebSocket, WebSocketDisconnect
from core.ws_manager import WSManager
from services.device_service import DeviceService
import json

class WSService:
    def __init__(self, ws_manager: WSManager, device_service: DeviceService):
        self.ws_manager = ws_manager
        self.device_service = device_service

    async def handle_connection(self, websocket: WebSocket, device_id: str):
        await self.ws_manager.connect(device_id, websocket)
        await self.device_service.set_device_status(device_id, 1)
        try:
            while True:
                raw = await websocket.receive_text()
                await self._process_message(device_id, raw)
        except WebSocketDisconnect:
            self.ws_manager.disconnect(device_id)
            await self.device_service.set_device_status(device_id, 0)

    async def _process_message(self, device_id: str, raw: str):
        try:
            data = json.loads(raw)
            # 处理不同类型的消息
            message_type = data.get("type")
            if message_type == "ping":
                # 回复 pong
                await self.send_to_device(device_id, json.dumps({"type": "pong"}))
            elif message_type == "status":
                # 处理状态更新
                pass
        except json.JSONDecodeError:
            # 消息不是有效的 JSON
            pass

    async def send_to_device(self, device_id: str, message: str) -> bool:
        return await self.ws_manager.send_to_device(device_id=device_id, message=message)
