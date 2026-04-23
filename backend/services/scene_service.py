from core.prompt import scene_detect_template
from services.llm_service import LLMService
class EmotionService:

    def __init__(self, llm_service, logger):
        self.llm:LLMService = llm_service
        self.logger = logger

    async def detect(self, text: str):


        reply_json=await self.llm.generate(scene_detect_template.render(input=text))     