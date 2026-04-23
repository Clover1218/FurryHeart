import requests
AI_API="https://apis.iflow.cn/v1/chat/completions"
API_KEY="sk-0ef0ddb37985e0dd458856157e34564b"


class iFlowClient:
    def __init__(self,model:str="qwen3-235b"):
        self.model=model
        pass
    async def chat(self,prompt:str,temperature:int=0.7):
        headers={
        "Authorization": "Bearer "+API_KEY,
        "Content-Type": "application/json"
        }
        data = {
            "model": self.model, 
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        response =requests.post(AI_API, json=data, headers=headers)
        result = response.json()
        return result["choices"][0]["message"]["content"]

