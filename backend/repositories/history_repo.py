import uuid
from typing import List, Optional
import asyncpg
from datetime import datetime, timezone

from repositories.history_models import (
    AddHistoryInput,
    AddHistoryOutput,
    GetRecentHistoryInput,
    GetRecentHistoryOutput,
    GetHistoryByCursorInput,
    GetHistoryByCursorOutput,
    ClearUserHistoryInput,
    ClearUserHistoryOutput,
    HistoryItem
)
from core.exceptions import AppException


class HistoryRepo:
    def __init__(self, db_pool: asyncpg.Pool, logger):
        self.db = db_pool
        self.logger = logger

    async def add_history(self, input_data: AddHistoryInput) -> AddHistoryOutput:
        """添加聊天历史"""
        query = """
        INSERT INTO chat_history (id, user_id, session_id, role, content)
        VALUES ($1, $2, $3, $4,$5)
        """

        try:
            async with self.db.acquire() as conn:
                await conn.execute(
                    query,
                    str(uuid.uuid4()),
                    input_data.user_id,
                    input_data.session_id,
                    input_data.role,
                    input_data.content
                )
            return AddHistoryOutput(success=True)
        except asyncpg.PostgresError as e:
            self.logger.error(f"添加聊天历史失败: {e}")
            raise AppException(message="数据库操作失败", code=500) from e

    async def get_recent_history(self, input_data: GetRecentHistoryInput) -> GetRecentHistoryOutput:
        """获取最近的聊天历史"""
        query = """
        SELECT role, content, created_at
        FROM chat_history
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """

        try:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(
                    query,
                    input_data.user_id,
                    input_data.limit
                )

            # 反转成正序
            rows.reverse()

            items = [
                HistoryItem(
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]

            return GetRecentHistoryOutput(items=items)
        except asyncpg.PostgresError as e:
            self.logger.error(f"获取聊天历史失败: {e}")
            raise AppException(message="数据库操作失败", code=500) from e

    async def get_history_by_cursor(self, input_data: GetHistoryByCursorInput) -> GetHistoryByCursorOutput:
        """根据游标获取聊天历史（支持增量操作）"""
        if input_data.cursor:
            query = """
            SELECT role, content, created_at
            FROM chat_history
            WHERE user_id = $1 AND created_at < $2
            ORDER BY created_at DESC
            LIMIT $3
            """
        else:
            query = """
            SELECT role, content, created_at
            FROM chat_history
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """

        try:
            async with self.db.acquire() as conn:
                if input_data.cursor:
                    rows = await conn.fetch(
                        query,
                        input_data.user_id,
                        input_data.cursor,
                        input_data.limit
                    )
                else:
                    rows = await conn.fetch(
                        query,
                        input_data.user_id,
                        input_data.limit
                    )

            # 转换为要求的格式: [{"role": "xxx", "text": "xxx"}, ...]
            next_cursor = None
            if rows:
                next_cursor = rows[-1]["created_at"]
            rows.reverse()            
            formatted_items = []
            for row in rows:
                role = row["role"]
                content = row["content"]
                formatted_items.append({"role": role, "text": content})

            # 计算下一个游标

            return GetHistoryByCursorOutput(
                items=formatted_items,
                next_cursor=next_cursor
            )
        except asyncpg.PostgresError as e:
            self.logger.error(f"根据游标获取聊天历史失败: {e}")
            raise AppException(message="数据库操作失败", code=500) from e

    async def clear_user_history(self, input_data: ClearUserHistoryInput) -> ClearUserHistoryOutput:
        """清空用户历史"""
        query = """
        DELETE FROM chat_history WHERE user_id = $1
        """

        try:
            async with self.db.acquire() as conn:
                await conn.execute(query, input_data.user_id)
            return ClearUserHistoryOutput(success=True)
        except asyncpg.PostgresError as e:
            self.logger.error(f"清空用户历史失败: {e}")
            raise AppException(message="数据库操作失败", code=500) from e
