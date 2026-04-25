import json
import re

from services.config_service import ConfigService
from services.emotion_service import EmotionService
from services.session_service import SessionService
from services.history_service import HistoryService
from services.memory_service import MemoryService
from services.llm_service import LLMService
from core.prompt import base_chat_template,system_base_prompt

import logging
class ChatOrchestrator:

    def __init__(self,
                 session_svc:SessionService,
                 emotion_svc:EmotionService,
                 history_svc:HistoryService,
                 memory_svc:MemoryService,
                 llm_svc:LLMService,
                 config_svc:ConfigService,
                 logger:logging.Logger):

        self.session_svc = session_svc

        self.emotion_svc = emotion_svc
        self.history_svc = history_svc
        self.memory_svc = memory_svc
        self.llm_svc = llm_svc
        self.config_svc = config_svc
        self.logger=logger

    async def chat(self, user_id, user_input):

        session = self.session_svc.get_session(user_id)
        if session["state"] == "STARTING":
            # emotion = await self.emotion_svc.detect(user_input)
            # session["emtion"]=emotion
            pass
        elif session["state"] == "CHATTING":
            pass
        session_id=session["session_id"]
        history_str = await self.history_svc.get_recent_history(user_id)
        # history_string = "\n".join(f"{item['role']}:{item['content']}" for item in history)
        await self.history_svc.add_history(user_id, session_id,"user", user_input)
        if user_input[0]=="!":
            await self.memory_svc.extract_memory(user_id,user_id,history_str)

            
        memories="" # await self.memory_svc.get_memory(user_id,user_input,user_input,5)
        memories_string='\n'.join(event['event_sentence'] for event in memories)

        user_config=await self.config_svc.get_user_final_config(user_id)
        print(type(user_config["prompt.system_base"]))
        system_base=json.loads(user_config["prompt.system_base"])['text']
        
        prompt=system_base+base_chat_template.render(history=history_str,input=user_input)

        
        reply = await self.llm_svc.generate(prompt)
        self.logger.info(reply)
        self.session_svc.update(user_id)

        await self.history_svc.add_history(user_id, session_id,"assistant", reply)
        return reply

    async def get_history_by_cursor(self, user_id, cursor=None, limit=20):
        """根据游标获取聊天历史"""
        return await self.history_svc.get_history_by_cursor(
            user_id=user_id,
            cursor=cursor,
            limit=limit
        )


    def _clean_code_block(self,raw_text: str) -> dict:
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"无法解析 JSON: {e}\n原始内容:\n{cleaned_text}")

        return data