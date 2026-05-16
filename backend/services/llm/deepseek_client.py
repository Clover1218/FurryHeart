import requests
AI_API="https://api.deepseek.com"

import os
from openai import OpenAI

class DeepSeekClient:
    def __init__(self,api_key):
        self.client = OpenAI(api_key,base_url=AI_API)      
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

