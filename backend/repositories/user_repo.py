import asyncpg
from core.exceptions import AppException
from repositories.user_models import GetMeBasicInfoInput,GetMeBasicInfoOutput
class UserRepo:

    def __init__(self, db_pool):
        self.db = db_pool
    async def get_me_basic_info(self,input_data:GetMeBasicInfoInput):
        async with self.db.acquire() as conn:
            try:
                user = await conn.fetchrow(
                    "SELECT nickname,avatar_url FROM user_info WHERE user_id = $1",
                    int(input_data.user_id)
                )
                
                if user:
                    return GetMeBasicInfoOutput(exist=True,nickname=user['nickname'],avatar_url=['avatar_url'])
                else:
                    return GetMeBasicInfoOutput(exist=False)
                
            except asyncpg.UniqueViolationError as e:
                raise AppException(message="用户已存在", code=409) from e
            except asyncpg.PostgresError as e:
                logging.error(f"数据库操作失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e




