import uuid
from typing import Any, Dict, List, Optional
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
            self.logger.error(f"添加聊天历史失败: {e}", exc_info=True)
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
            self.logger.error(f"获取聊天历史失败: {e}", exc_info=True)
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
            self.logger.error(f"根据游标获取聊天历史失败: {e}", exc_info=True)
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
            self.logger.error(f"清空用户历史失败: {e}", exc_info=True)
            raise AppException(message="数据库操作失败", code=500) from e

    async def get_history_by_session_id(self, session_id: str) -> list:
        """根据会话ID获取聊天历史
        
        Args:
            session_id: 会话ID
        
        Returns:
            聊天历史列表，格式为 [{"role": "xxx", "content": "xxx"}, ...]
        """
        query = """
        SELECT role, content, created_at
        FROM chat_history
        WHERE session_id = $1
        ORDER BY created_at ASC
        """

        try:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(query, session_id)

            history = []
            for row in rows:
                history.append({
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"]
                })

            return history
        except asyncpg.PostgresError as e:
            self.logger.error(f"根据会话ID获取聊天历史失败: {e}", exc_info=True)
            raise AppException(message="数据库操作失败", code=500) from e

    async def query_history_by_time(self,
                                    user_id: str,device_id: str,
                                    start_time: datetime,end_time: datetime,
                                    max_turns: int = 30) -> tuple[str, Dict[str, Any]]:
        query = """
        SELECT session_id, role, content, created_at
            FROM chat_history
            WHERE user_id = $1
              AND created_at BETWEEN $2 AND $3
            ORDER BY session_id, created_at
        """
        try:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(query,user_id, start_time, end_time)
                sessions: Dict[str, Dict] = {}
                for row in rows:
                    sid = row["session_id"]
                    if sid not in sessions:
                        sessions[sid] = {
                            "start_time": row["created_at"],
                            "end_time": row["created_at"],
                            "messages": []
                        }
                    sessions[sid]["messages"].append({
                        "role": row["role"],
                        "text": row["content"]
                    })
                    # 更新时间边界
                    if row["created_at"] < sessions[sid]["start_time"]:
                        sessions[sid]["start_time"] = row["created_at"]
                    if row["created_at"] > sessions[sid]["end_time"]:
                        sessions[sid]["end_time"] = row["created_at"]
            segments = []
            total_turns = 0
            truncated = False

            for sid, data in sessions.items():
                msg_list = data["messages"]
                turn_count = len(msg_list)

                # 如果累计消息超过 max_turns，截断
                if total_turns + turn_count > max_turns:
                    remaining = max_turns - total_turns
                    if remaining <= 0:
                        truncated = True
                        break
                    msg_list = msg_list[:remaining]
                    turn_count = len(msg_list)
                    truncated = True

                segments.append({
                    "session_id": sid,
                    "start_time": data["start_time"].isoformat(),
                    "end_time": data["end_time"].isoformat(),
                    "turn_count": turn_count,
                    "messages": msg_list
                })
                total_turns += turn_count

            # 4. 构建返回的 artifact（结构化数据，供后续步骤使用）
            artifact = {
                "segments": segments,
                "total_turns": total_turns,
                "truncated": truncated,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }

            # 5. 生成给 LLM 的自然语言摘要（作为 content）
            if total_turns == 0:
                content = "未找到该时间范围内的历史记录。"
            else:
                seg_summary = []
                for seg in segments:
                    seg_summary.append(
                        f"会话 {seg['session_id'][:8]}... "
                        f"({seg['start_time'][:16]} ~ {seg['end_time'][:16]}, "
                        f"共{seg['turn_count']}条消息)"
                    )
                summary_text = "找到以下历史对话段落：\n" + "\n".join(seg_summary)
                if truncated:
                    summary_text += "\n（注意：返回内容已截断，仅显示部分消息）"
                content = summary_text
            return content, artifact
        except asyncpg.PostgresError as e:
            self.logger.error(e)
            raise AppException(message="数据库操作失败", code=500) from e