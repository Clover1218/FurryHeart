"""
TTS Service：语音合成服务封装

提供流式音频合成接口，支持：
- 单次合成：synthesize(text) -> bytes
- 流式合成：synthesize_stream(text) -> AsyncIterator[bytes]

用法：
    # 流式合成（适用于实时语音响应场景）
    async for chunk in tts_service.synthesize_stream("你好"):
        await websocket.send_bytes(chunk)
"""
import asyncio
import os
import re
import sys
import threading
from typing import AsyncIterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENT_END_RE = re.compile(r"[。！？!?…]")
MIN_SENTENCE_LEN = 6
END_MARKER = "[END]"


def _check_and_strip_end(text: str) -> tuple[str, bool]:
    """检查文本中是否包含 [END]，返回 (清理后文本, 是否找到)"""
    if END_MARKER in text:
        return text.split(END_MARKER)[0], True
    return text, False


def _pop_sentence(buf: str) -> tuple[str, str]:
    """从 token 缓冲区提取第一个完整句子。

    返回 (sentence, remaining)。
    若未找到句子边界，sentence 为空字符串。
    """
    for i, ch in enumerate(buf):
        if SENT_END_RE.match(ch) and i + 1 >= MIN_SENTENCE_LEN:
            return buf[: i + 1].strip(), buf[i + 1 :]
    return "", buf
class TTSService:
    """阿里云 CosyVoice 流式语音合成服务"""

    def __init__(self,model="cosyvoice-v2",voice="aries_emo",api_key=""):
        self._model=model
        self._voice=voice
        self._sample_rate = 16000
        self._format = "pcm"
        self._api_key = api_key
    async def return_audio_generator(self,
        token_stream: AsyncIterator[str],
    ) -> tuple[AsyncIterator[bytes], list[str], list[bool]]:
        """将 LLM token 流转换为 TTS 音频流

        参数：
            token_stream: LLM 输出的 token 流（AsyncIterator[str]）

        返回：
            audio_gen : AsyncIterator[bytes]，TTS 合成的 PCM 音频流
            reply_parts : list[str]，所有 token 的列表（可拼接成完整回复）
            goodbye : list[bool]，[True] 表示检测到 [END] 结束标记

    用法：
        audio_gen, reply_parts, goodbye = stream_tokens_to_audio(
            llm.stream_chat(messages)
        )

        async for chunk in audio_gen:
            await websocket.send_bytes(chunk)

            full_reply = "".join(reply_parts)
            is_goodbye = goodbye[0]
        """
        reply_parts: list[str] = []
        goodbye: list[bool] = [False]  # 用 list 包装，闭包内可修改
        sentence_buf = ""

        async def audio_gen() -> AsyncIterator[bytes]:
            nonlocal sentence_buf, goodbye

            async def _send_sentence(sentence: str) -> AsyncIterator[bytes]:
                """送一句话给 TTS，先检查并剥离 [END]"""
                nonlocal goodbye
                sentence, found = _check_and_strip_end(sentence)
                if found:
                    goodbye[0] = True
                sentence = sentence.strip()
                if sentence and any('\u4e00' <= c <= '\u9fff' or c.isalnum() for c in sentence):
                    async for chunk in self.synthesize_stream(sentence):
                        yield chunk

            async def _consume_tokens() -> AsyncIterator[bytes]:
                """消费 token 源，累积→切句→送 TTS"""
                nonlocal sentence_buf, goodbye

                async for token in token_stream:
                    reply_parts.append(token)
                    sentence_buf += token

                    # 检测跨 token 的 [END]
                    if END_MARKER in sentence_buf:
                        sentence_buf = sentence_buf.split(END_MARKER)[0]
                        goodbye[0] = True
                        break

                    # 尝试切分句子
                    sentence, sentence_buf = _pop_sentence(sentence_buf)
                    if sentence:
                        async for chunk in _send_sentence(sentence):
                            yield chunk

            try:
                async for chunk in _consume_tokens():
                    yield chunk
            except Exception as e:
                print(f"[!] TTS 流处理异常: {e}")
                import traceback
                traceback.print_exc()

            # 尾部残余文本
            tail = sentence_buf.strip()
            if tail and any('\u4e00' <= c <= '\u9fff' or c.isalnum() for c in tail):
                async for chunk in _send_sentence(tail):
                    yield chunk

        return audio_gen(), reply_parts, goodbye


    def synthesize(self, text: str) -> bytes:
        """同步合成完整音频

        Args:
            text: 待合成的文字

        Returns:
            16kHz 16bit mono PCM 音频数据
        """
        import dashscope
        from dashscope.audio.tts_v2 import AudioFormat, ResultCallback, SpeechSynthesizer

        dashscope.api_key = self._api_key
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio._get_running_loop()

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        class _Callback(ResultCallback):
            def on_open(self) -> None:
                pass

            def on_close(self) -> None:
                pass

            def on_complete(self) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, None)

            def on_error(self, message: str) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, RuntimeError(f"TTS 错误: {message}"))

            def on_data(self, data: bytes) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, data)

        syn = SpeechSynthesizer(
            model=self._model,
            voice=self._voice,
            format=AudioFormat.PCM_16000HZ_MONO_16BIT,
            callback=_Callback(),
        )

        def _run() -> None:
            syn.streaming_call(text)
            syn.streaming_complete()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        audio_chunks = []
        while True:
            item = queue.get()
            if item is None:
                break
            if isinstance(item, RuntimeError):
                raise item
            audio_chunks.append(item)

        thread.join(timeout=10)
        return b"".join(audio_chunks)

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """流式合成语音，逐块 yield PCM 音频数据

        每次调用建立一个 TTS 会话，适合逐句调用。

        Args:
            text: 待合成的文字

        Yields:
            PCM 音频数据块
        """
        import dashscope
        from dashscope.audio.tts_v2 import AudioFormat, ResultCallback, SpeechSynthesizer

        dashscope.api_key = self._api_key

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        class _Callback(ResultCallback):
            def on_open(self) -> None:
                pass

            def on_close(self) -> None:
                pass

            def on_complete(self) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, None)

            def on_error(self, message: str) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, RuntimeError(f"TTS 错误: {message}"))

            def on_data(self, data: bytes) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, data)

        syn = SpeechSynthesizer(
            model=self._model,
            voice=self._voice,
            format=AudioFormat.PCM_16000HZ_MONO_16BIT,
            callback=_Callback(),
        )

        def _run() -> None:
            syn.streaming_call(text)
            syn.streaming_complete()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, RuntimeError):
                raise item
            yield item

        thread.join(timeout=10)
    

tts_service = TTSService()
