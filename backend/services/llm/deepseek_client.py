import requests
AI_API="https://api.deepseek.com"

import os
from openai import OpenAI
from typing import AsyncIterator

class DeepSeekClient:
    def __init__(self,api_key):
        self.client = OpenAI(api_key=api_key,base_url=AI_API)      
    
    async def chat(self,prompt:str,temperature:int=0.7):
        response = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "user", "content": prompt},
            ],
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    async def chat_stream(self,prompt:str,temperature:int=0.7) -> AsyncIterator[str]:
        """流式调用 DeepSeek API"""
        stream = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "user", "content": prompt},
            ],
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
            temperature=temperature,
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

