import requests
API_KEY="sk-de20a591dcfd4f9e907164628eccc331"
AI_API="https://api.deepseek.com"

import os
from openai import OpenAI

class DeepSeekClient:
    def __init__(self):
        self.client = OpenAI(api_key=API_KEY,base_url=AI_API)      
    async def chat(self,prompt:str,temperature:int=0.7):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=temperature,
        )
        return response.choices[0].message.content

