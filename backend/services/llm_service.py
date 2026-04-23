class LLMService:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    async def generate(self, prompt: str, temperature=0.7):

        self.logger.info(prompt)

        resp = await self.client.chat(prompt, temperature)

        self.logger.info("[llm] response received")

        return resp