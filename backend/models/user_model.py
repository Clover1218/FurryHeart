from pydantic import BaseModel, Field, EmailStr


class GetMeBasicInfoResponse(BaseModel):
    nickname:str
    avatar_url:str