from fastapi import WebSocket, WebSocketDisconnect
from orchestrator.chat_orchestator import ChatOrchestrator
from core.config import SAMPLE_RATE
from services.asr_service import ASRService
from services.tts_service import TTSService
from core.ws_manager import WSManager
from services.device_service import DeviceService
import json

class WSService:
    def __init__(self, ws_manager: WSManager, device_service: DeviceService,asr_service:ASRService,tts_service:TTSService,chat_orchestrator:ChatOrchestrator):
        self.ws_manager = ws_manager
        self.device_service = device_service
        self.asr_service = asr_service
        self.tts_service = tts_service
        self.chat_orchestrator = chat_orchestrator
        self._voice_states = {}
        


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
                    break
                
                if "bytes" in message:
                    # 处理二进制音频数据
                    await self._handle_audio(device_id, message["bytes"])
                elif "text" in message:
                    # 处理文本消息
                    await self._process_message(websocket,device_id, message["text"])
            
        except WebSocketDisconnect:
            self.ws_manager.disconnect(device_id)
            await self.device_service.update_device_status(device_id, 'offline')


    async def _handle_audio(self, device_id: str, pcm_bytes: bytes):
        """处理二进制音频数据"""
        state = self._voice_states.get(device_id)
        if state and state["recording"]:
            state["audio_buffer"].extend(pcm_bytes)




    async def _process_message(self, connection:WebSocket,device_id: str, raw: str):
        try:
            data = json.loads(raw)
            self._process_audio_message(connection,device_id,raw)
            
        except json.JSONDecodeError:
            # 消息不是有效的 JSON
            pass

    async def _process_audio_message(self,connection:WebSocket,device_id:str,data:str):
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
            # ── 全链路处理：ASR → LLM（Tool Calling）→ TTS ──
            user_text=await self.asr_service.transcribe(pcm)
            if user_text:
                reply_stream_iter=self.chat_orchestrator.chat_stream(device_id,user_text)


                audio_generator,reply_parts,goodbye=self.tts_service.return_audio_generator(reply_stream_iter)
                # 流式发送 TTS 音频给 ESP32
                async for chunk in audio_generator:
                    await connection.send_bytes(chunk)
                # 发送 ping 作为音频结束信号
                await connection.ping()
                # 如果 LLM 判断用户想结束对话，发送 goodbye 事件
                if goodbye[0]:
                    await connection.send_text(json.dumps({"event": "goodbye"}))
                    print("[会话] 发送 goodbye 信号")
                # 更新对话历史（清理 [END] 标记，只保存纯文本回复）
                full_reply = "".join(reply_parts).replace("[END]", "").strip()
                # history.append({"role": "user", "content": user_text})
                # history.append({"role": "assistant", "content": full_reply})
                # if scene_id[0]:
                #     print(f"[场景] {scene_id[0]}")
                print(f"[回复] {full_reply}")
            else:
                # ASR 未识别到语音，发送静音块 + ping 让 ESP32 继续工作
                # 必须发送至少一个音频块，否则 ESP32 的 isStreamingActive() 为 false，ping 会被忽略
                print(f"[{device_id}] ASR 未识别到语音，发送静音信号")
                silence = b'\x00' * 3200  # 0.1秒静音 (16000Hz * 2bytes * 0.1s)
                await connection.send_bytes(silence)
                await connection.ping()
        elif event == "recording_cancelled":
            print(f"[{device_id}] 录音取消（录音过短或用户未说话）")
            self._voice_states[device_id]["recording"] = False
            self._voice_states[device_id]["audio_buffer"] = bytearray()

    async def send_to_device(self, device_id: str, message: str) -> bool:
        return await self.ws_manager.send_to_device(device_id=device_id, message=message)
