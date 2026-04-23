from pydantic import BaseModel, Field

class WeChatLoginRequest(BaseModel):
    code: str 

class WeChatLoginResponse(BaseModel):
    access_token: str
    is_new: bool = False
    open_id: str = ""
    name: str = ""
    avatar: str = ""
    