from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class GetMeBasicInfoInput:
    user_id:str

    
@dataclass(frozen=True)    
class GetMeBasicInfoOutput:
    exist:bool
    nickname:str
    avatar_url:str