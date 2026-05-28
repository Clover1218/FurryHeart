from typing import AsyncIterator


class LLMService:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    async def generate(self, prompt: str, temperature=0.7):

        self.logger.info(prompt)

        resp = await self.client.chat(prompt, temperature)

        self.logger.info("[llm] response received")

        return resp
    
    async def generate_stream(self, prompt: str, temperature=0.7) -> AsyncIterator[str]:
        """流式生成响应"""
        self.logger.info("[llm] streaming request")
        
        async for chunk in self.client.chat_stream(prompt, temperature):
            yield chunk
        
        self.logger.info("[llm] streaming response completed")