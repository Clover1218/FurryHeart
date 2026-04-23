from core.exceptions import AppException
from repositories.user_models import (
    GetMeBasicInfoInput,
    GetMeBasicInfoOutput
)

from repositories.user_repo import UserRepo
class UserService:
    def __init__(self, user_repo, logger):
        self.user_repo:UserRepo = user_repo
        self.logger = logger

    async def get_me_basic_info(self,user_id:str)-> tuple[str,str]:
        output:GetMeBasicInfoOutput=await self.user_repo.get_me_basic_info(GetMeBasicInfoInput(user_id=user_id))
        if output.exist==False:
            raise AppException(message="查无此人",code=500)
        return output.nickname,output.avatar_url

        
    