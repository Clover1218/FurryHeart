# services/history_service.py

from datetime import datetime
from typing import Any, Dict, List
from repositories.history_repo import HistoryRepo
from repositories.history_models import (
    AddHistoryInput,
    GetRecentHistoryInput,
    ClearUserHistoryInput,
    HistoryItem
)


class HistoryService:

    def __init__(self, history_repo: HistoryRepo, logger, max_turns=10):
        self.history_repo = history_repo
        self.logger = logger
        self.max_turns = max_turns  # 控制上下文长度

    async def add_history(self, user_id, session_id,role, content):
        input_data = AddHistoryInput(
            user_id=user_id,
            role=role,
            content=content,
            session_id=session_id
        )
        await self.history_repo.add_history(input_data)

    async def get_recent_history(self, user_id):
        input_data = GetRecentHistoryInput(
            user_id=user_id,
            limit=self.max_turns * 2  # user + assistant
        )
        result = await self.history_repo.get_recent_history(input_data)

        # 转换为字符串格式
        history_str = ""
        for item in result.items:
            role = item.role
            content = item.content
            if role == "assistant":
                history_str += f"绒绒:{content}\n"
            elif role == "user":
                history_str += f"用户:{content}\n"

        return history_str

    async def clear_user_history(self, user_id):
        input_data = ClearUserHistoryInput(user_id=user_id)
        await self.history_repo.clear_user_history(input_data)

    async def get_history_by_cursor(self, user_id, cursor=None, limit=20):
        """根据游标获取聊天历史"""
        from repositories.history_models import GetHistoryByCursorInput
        input_data = GetHistoryByCursorInput(
            user_id=user_id,
            cursor=cursor,
            limit=limit
        )
        return await self.history_repo.get_history_by_cursor(input_data)

    async def get_history_by_session_id(self, session_id):
        """根据会话ID获取聊天历史"""
        return await self.history_repo.get_history_by_session_id(session_id)
    async def query_history_by_time(self,
                                    user_id: str,device_id: str,
                                    start_time: datetime,end_time: datetime,
                                    max_turns: int = 30) -> tuple[str, Dict[str, Any]]:
        return await self.history_repo.query_history_by_time(user_id,device_id,start_time,end_time,max_turns)
    
    async def get_previous_history(self,user_id:str,device_id:str) -> List[HistoryItem]:
        input_data = GetRecentHistoryInput(
            user_id=user_id,
            limit=self.max_turns * 2  # user + assistant
        )
        result = await self.history_repo.get_recent_history(input_data)
        return result.items
        