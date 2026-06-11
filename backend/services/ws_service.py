from fastapi import WebSocket, WebSocketDisconnect
from orchestrator.chat_orchestator import ChatOrchestrator
from core.config import SAMPLE_RATE
from services.asr_service import ASRService
from services.tts_service import TTSService
from core.ws_manager import WSManager
from services.device_service import DeviceService
import json
import logging

logger = logging.getLogger(__name__)


class WSService:
    def __init__(self, ws_manager: WSManager, device_service: DeviceService, asr_service: ASRService, tts_service: TTSService, chat_orchestrator: ChatOrchestrator):
        self.ws_manager = ws_manager
        self.device_service = device_service
        self.asr_service = asr_service
        self.tts_service = tts_service
        self.chat_orchestrator = chat_orchestrator
        self._voice_states = {}
        self._pending_binds: dict[str, str] = {}
        self._pending_unbinds: dict[str, str] = {}

    async def handle_connection(self, websocket: WebSocket, device_id: str):
        await self.ws_manager.connect(device_id, websocket)
        await self.device_service.update_device_status(device_id, 'active')
        self._voice_states[device_id] = {
            "recording": False,
            "audio_buffer": bytearray(),
            "history": []
        }
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    self.ws_manager.disconnect(device_id)
                    await self.device_service.update_device_status(device_id, 'offline')
                    self._cleanup_device(device_id)
                    break

                if "bytes" in message:
                    await self._handle_audio(device_id, message["bytes"])
                elif "text" in message:
                    await self._process_message(websocket, device_id, message["text"])

        except WebSocketDisconnect:
            self.ws_manager.disconnect(device_id)
            await self.device_service.update_device_status(device_id, 'offline')
            self._cleanup_device(device_id)

    def _cleanup_device(self, device_id: str):
        self._voice_states.pop(device_id, None)
        self._pending_binds.pop(device_id, None)
        self._pending_unbinds.pop(device_id, None)

    async def _handle_audio(self, device_id: str, pcm_bytes: bytes):
        state = self._voice_states.get(device_id)
        if state and state["recording"]:
            state["audio_buffer"].extend(pcm_bytes)

    async def _process_message(self, connection: WebSocket, device_id: str, raw: str):
        try:
            data = json.loads(raw)
            event = data.get("event")
            if event in ("wake_word_detected", "recording_started", "recording_ended", "recording_cancelled"):
                await self._process_audio_message(connection, device_id, data)
            elif event in ("device_send_bind_token", "device_bind_result_confirm"):
                await self._process_bind_message(connection, device_id, data)
            elif event in ("device_send_unbind_token", "device_unbind_result_confirm"):
                await self._process_unbind_message(connection, device_id, data)
            else:
                logger.warning(f"[{device_id}] 未知事件: {event}")
        except json.JSONDecodeError:
            logger.warning(f"[{device_id}] 收到非 JSON 消息: {raw[:100]}")

    async def _process_audio_message(self, connection: WebSocket, device_id: str, data: dict):
        event = data.get("event")
        if event == "wake_word_detected":
            print("唤醒词检测到")

        elif event == "recording_started":
            print("开始录音")
            self._voice_states[device_id]["recording"] = True
            self._voice_states[device_id]["audio_buffer"] = bytearray()
        elif event == "recording_ended":
            self._voice_states[device_id]["recording"] = False
            pcm = bytes(self._voice_states[device_id]["audio_buffer"])
            self._voice_states[device_id]["audio_buffer"] = bytearray()
            duration = len(pcm) / (SAMPLE_RATE * 2)
            print(f"[{device_id}] 录音结束，时长 {duration:.2f}s，大小 {len(pcm)} bytes")
            user_text = await self.asr_service.transcribe(pcm)
            if user_text:
                reply_stream_iter = self.chat_orchestrator.chat_stream(device_id, user_text)

                audio_generator, reply_parts, goodbye = await self.tts_service.return_audio_generator(reply_stream_iter)
                async for chunk in audio_generator:
                    await connection.send_bytes(chunk)
                await connection.send_text(json.dumps({"event": "audio_stream_end"}))
                if goodbye[0]:
                    await connection.send_text(json.dumps({"event": "goodbye"}))
                    print("[会话] 发送 goodbye 信号")
                full_reply = "".join(reply_parts).replace("[END]", "").strip()
                print(f"[回复] {full_reply}")
            else:
                print(f"[{device_id}] ASR 未识别到语音，发送静音信号")
                silence = b'\x00' * 3200
                await connection.send_bytes(silence)
                await connection.send_text(json.dumps({"event": "audio_stream_end"}))
        elif event == "recording_cancelled":
            print(f"[{device_id}] 录音取消（录音过短或用户未说话）")
            self._voice_states[device_id]["recording"] = False
            self._voice_states[device_id]["audio_buffer"] = bytearray()

    async def _process_bind_message(self, connection: WebSocket, device_id: str, data: dict):
        event = data.get("event")
        if event == "device_send_bind_token":
            await self._handle_device_send_bind_token(connection, device_id, data)
        elif event == "device_bind_result_confirm":
            await self._handle_device_bind_result_confirm(connection, device_id, data)

    async def _handle_device_send_bind_token(self, connection: WebSocket, device_id: str, data: dict):
        """处理硬件发来的绑定 token 验证请求

        流程:
        1. 从消息中提取 token
        2. 从 Redis 中消费（获取并删除）token 数据
        3. 验证 token 中的 device_id 与当前 WS 连接的 device_id 一致
        4. 向硬件发送验证结果（server_send_bind_result）
        """
        token = data.get("data", {}).get("token")
        if not token:
            logger.warning(f"[{device_id}] 绑定 token 为空")
            await self._send_bind_result(connection, success=False)
            return

        token_data = await self.device_service.consume_bind_token(token)
        if token_data is None:
            logger.warning(f"[{device_id}] 绑定 token 无效或已过期: {token[:8]}...")
            await self._send_bind_result(connection, success=False)
            return

        token_device_id = token_data["device_id"]
        if token_device_id != device_id:
            logger.warning(f"[{device_id}] 绑定 token 设备不匹配: token属于 {token_device_id}")
            await self._send_bind_result(connection, success=False)
            return

        user_id = token_data["user_id"]
        self._pending_binds[device_id] = user_id
        logger.info(f"[{device_id}] 绑定 token 验证成功，用户: {user_id}")
        await self._send_bind_result(connection, success=True, user_id=user_id)

    async def _send_bind_result(self, connection: WebSocket, success: bool, user_id: str = None):
        """向硬件发送绑定验证结果

        Args:
            connection: WebSocket 连接
            success: 是否验证成功
            user_id: 验证成功时携带的用户ID
        """
        payload = {
            "event": "server_send_bind_result",
            "data": {
                "success": success
            }
        }
        if success and user_id:
            payload["data"]["user_id"] = user_id
        await connection.send_text(json.dumps(payload))

    async def _handle_device_bind_result_confirm(self, connection: WebSocket, device_id: str, data: dict):
        """处理硬件对绑定结果的确认

        流程:
        1. 硬件处理完绑定结果后，回复确认消息
        2. 如果硬件确认成功，在数据库中完成设备绑定
        3. 如果硬件确认失败，记录错误日志，清除待绑定信息
        """
        confirm_data = data.get("data", {})
        success = confirm_data.get("success", False)
        error_msg = confirm_data.get("error_msg", "")

        if success:
            user_id = self._pending_binds.pop(device_id, None)
            if user_id:
                bound = await self.device_service.bind_device(device_id, user_id)
                if bound:
                    logger.info(f"[{device_id}] 设备绑定成功，用户: {user_id}")
                else:
                    logger.error(f"[{device_id}] 设备绑定到数据库失败，用户: {user_id}", exc_info=True)
            else:
                logger.warning(f"[{device_id}] 收到硬件绑定确认，但未找到待绑定信息")
        else:
            self._pending_binds.pop(device_id, None)
            logger.error(f"[{device_id}] 硬件确认绑定失败: {error_msg}")

    async def _process_unbind_message(self, connection: WebSocket, device_id: str, data: dict):
        event = data.get("event")
        if event == "device_send_unbind_token":
            await self._handle_device_send_unbind_token(connection, device_id, data)
        elif event == "device_unbind_result_confirm":
            await self._handle_device_unbind_result_confirm(connection, device_id, data)

    async def _handle_device_send_unbind_token(self, connection: WebSocket, device_id: str, data: dict):
        """处理硬件发来的解绑 token 验证请求

        流程:
        1. 从消息中提取 token
        2. 从 Redis 中消费（获取并删除）token 数据
        3. 验证 token 中的 device_id 与当前 WS 连接的 device_id 一致
        4. 向硬件发送验证结果（server_send_unbind_result）
        """
        token = data.get("data", {}).get("token")
        if not token:
            logger.warning(f"[{device_id}] 解绑 token 为空")
            await self._send_unbind_result(connection, success=False)
            return

        token_data = await self.device_service.consume_unbind_token(token)
        if token_data is None:
            logger.warning(f"[{device_id}] 解绑 token 无效或已过期: {token[:8]}...")
            await self._send_unbind_result(connection, success=False)
            return

        token_device_id = token_data["device_id"]
        if token_device_id != device_id:
            logger.warning(f"[{device_id}] 解绑 token 设备不匹配: token属于 {token_device_id}")
            await self._send_unbind_result(connection, success=False)
            return

        user_id = token_data["user_id"]
        self._pending_unbinds[device_id] = user_id
        logger.info(f"[{device_id}] 解绑 token 验证成功，用户: {user_id}")
        await self._send_unbind_result(connection, success=True, user_id=user_id)

    async def _send_unbind_result(self, connection: WebSocket, success: bool, user_id: str = None):
        """向硬件发送解绑验证结果

        Args:
            connection: WebSocket 连接
            success: 是否验证成功
            user_id: 验证成功时携带的用户ID（只有success为true时才填写）
        """
        payload = {
            "event": "server_send_unbind_result",
            "data": {
                "success": success
            }
        }
        if success and user_id:
            payload["data"]["user_id"] = user_id
        await connection.send_text(json.dumps(payload))

    async def _handle_device_unbind_result_confirm(self, connection: WebSocket, device_id: str, data: dict):
        """处理硬件对解绑结果的确认

        流程:
        1. 硬件处理完解绑结果后，回复确认消息
        2. 如果硬件确认成功，在数据库中完成设备解绑
        3. 如果硬件确认失败，记录错误日志，清除待解绑信息
        """
        confirm_data = data.get("data", {})
        success = confirm_data.get("success", False)
        error_msg = confirm_data.get("error_msg", "")

        if success:
            user_id = self._pending_unbinds.pop(device_id, None)
            if user_id:
                unbound = await self.device_service.unbind_device(device_id)
                if unbound:
                    logger.info(f"[{device_id}] 设备解绑成功，用户: {user_id}")
                else:
                    logger.error(f"[{device_id}] 设备解绑到数据库失败，用户: {user_id}", exc_info=True)
            else:
                logger.warning(f"[{device_id}] 收到硬件解绑确认，但未找到待解绑信息")
        else:
            self._pending_unbinds.pop(device_id, None)
            logger.error(f"[{device_id}] 硬件确认解绑失败: {error_msg}")

    async def send_to_device(self, device_id: str, message: str) -> bool:
        return await self.ws_manager.send_to_device(device_id=device_id, message=message)
