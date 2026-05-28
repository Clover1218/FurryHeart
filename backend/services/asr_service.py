"""
ASR Service：语音识别服务封装

提供流式音频识别接口，支持：
- 单次识别：transcribe(pcm_bytes) -> str
- 流式识别：aiter_transcribe(pcm_stream) -> AsyncIterator[str]

用法：
    # 单次识别
    text = await asr_service.transcribe(pcm_bytes)

    # 流式识别（适用于实时转写场景）
    async for text_segment in asr_service.aiter_transcribe(audio_stream):
        print(f"识别到: {text_segment}")
"""
import asyncio
import os
import sys
import tempfile
import wave
from typing import AsyncIterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ASRService:
    """阿里云 Paraformer 语音识别服务"""

    def __init__(self,sample_rate=16000,model="paraformer-realtime-v2",api_key=""):
        self._sample_rate = sample_rate
        self._model = model
        self._min_audio_duration = 0.2
        self._api_key=api_key

    def _recognize_sync(self, wav_path: str) -> str:
        """同步 ASR 调用（在线程中运行）"""
        import dashscope
        from dashscope.audio.asr import Recognition, RecognitionCallback

        dashscope.api_key = self._api_key

        recognizer = Recognition(
            model=self._model,
            format="wav",
            sample_rate=self._sample_rate,
            callback=RecognitionCallback(),
        )
        result = recognizer.call(wav_path)

        if result.status_code != 200:
            raise RuntimeError(f"ASR 错误 {result.code}: {result.message}")

        if not result.output:
            return ""

        sentences = result.output.get("sentence", [])
        return "".join(s.get("text", "") for s in sentences).strip()

    async def transcribe(self, pcm_bytes: bytes) -> str:
        """将 PCM 音频字节识别为文字

        Args:
            pcm_bytes: 16kHz 16bit mono PCM 音频数据

        Returns:
            识别出的文字字符串
        """
        min_bytes = int(self._sample_rate * 2 * self._min_audio_duration)
        if len(pcm_bytes) < min_bytes:
            return ""

        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._sample_rate)
                wf.writeframes(pcm_bytes)

            return await asyncio.to_thread(self._recognize_sync, wav_path)
        finally:
            os.unlink(wav_path)

    async def aiter_transcribe(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """流式识别接口

        持续接收音频流片段，实时识别并 yield 文字结果。

        Args:
            audio_stream: PCM 音频流

        Yields:
            识别出的文字片段
        """
        buffer = bytearray()
        chunk_size = int(self._sample_rate * 2 * 0.5)

        async for chunk in audio_stream:
            buffer.extend(chunk)
            if len(buffer) >= chunk_size:
                result = await self.transcribe(bytes(buffer))
                if result:
                    yield result
                buffer.clear()

        if buffer:
            result = await self.transcribe(bytes(buffer))
            if result:
                yield result


asr_service = ASRService()
