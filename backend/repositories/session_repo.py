"""会话数据访问层"""

import uuid
from datetime import datetime, timezone

import asyncpg


class SessionRepo:
    def __init__(self, db_pool: asyncpg.Pool, logger):
        self.db = db_pool
        self.logger = logger

    async def create_session(self, user_id: str, device_id: str = "") -> dict:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        query = """
        INSERT INTO sessions (
            id, user_id, device_id, session_id,
            start_time, last_active, turn_count, state, memory_extracted
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                str(uuid.uuid4()),
                user_id,
                device_id,
                session_id,
                now,
                now,
                0,
                "STARTING",
                False
            )
            return self._row_to_dict(row)

    async def get_session(self, user_id: str, session_id: str = "") -> dict:
        """获取用户会话"""
        if session_id:
            query = """
            SELECT * FROM sessions
            WHERE user_id = $1 AND session_id = $2
            ORDER BY last_active DESC LIMIT 1
            """
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(query, user_id, session_id)
                return self._row_to_dict(row) if row else None

        query = """
        SELECT * FROM sessions
        WHERE user_id = $1
        ORDER BY last_active DESC LIMIT 1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            return self._row_to_dict(row) if row else None

    async def update_session(self, session_id: str, updates: dict) -> bool:
        """更新会话信息"""
        clauses = []
        params = []
        idx = 1

        if 'last_active' in updates:
            clauses.append(f"last_active = ${idx}")
            params.append(updates['last_active'])
            idx += 1

        if 'turn_count' in updates:
            clauses.append(f"turn_count = ${idx}")
            params.append(updates['turn_count'])
            idx += 1

        if 'state' in updates:
            clauses.append(f"state = ${idx}")
            params.append(updates['state'])
            idx += 1

        if 'emotion' in updates:
            clauses.append(f"emotion = ${idx}")
            params.append(updates['emotion'])
            idx += 1

        if 'memory_extracted' in updates:
            clauses.append(f"memory_extracted = ${idx}")
            params.append(updates['memory_extracted'])
            idx += 1

        clauses.append(f"updated_at = NOW()")
        params.append(session_id)

        if not clauses:
            return False

        query = f"UPDATE sessions SET {', '.join(clauses)} WHERE session_id = ${idx}"
        async with self.db.acquire() as conn:
            result = await conn.execute(query, *params)
            return result != "UPDATE 0"

    async def get_sessions_needing_memory_extraction(self, threshold_minutes: int) -> list:
        """获取需要提取记忆的会话"""
        query = """
        SELECT * FROM sessions
        WHERE state = 'CHATTING' AND memory_extracted = false
          AND start_time < NOW() - INTERVAL '1 minute' * $1
        ORDER BY start_time ASC
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, threshold_minutes)
            return [self._row_to_dict(row) for row in rows]

    async def get_latest_unextracted_session(self, user_id: str = "") -> dict:
        """获取最新的未提取记忆的会话
        
        Args:
            user_id: 用户ID（可选），不传则获取所有用户的
        
        Returns:
            会话信息或 None
        """
        if user_id:
            query = """
            SELECT * FROM sessions
            WHERE user_id = $1 AND memory_extracted = false
            ORDER BY start_time DESC
            LIMIT 1
            """
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(query, user_id)
                return self._row_to_dict(row) if row else None
        else:
            query = """
            SELECT * FROM sessions
            WHERE memory_extracted = false
            ORDER BY start_time DESC
            LIMIT 1
            """
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(query)
                return self._row_to_dict(row) if row else None

    async def cleanup_expired_sessions(self, timeout_minutes: int) -> int:
        """清理超时会话"""
        query = """
        DELETE FROM sessions
        WHERE last_active < NOW() - INTERVAL '1 minute' * $1
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, timeout_minutes)
            deleted_count = int(result.split()[1]) if result.startswith("DELETE") else 0
            self.logger.info(f"[SessionRepo] 清理了 {deleted_count} 个超时会话")
            return deleted_count

    def _row_to_dict(self, row) -> dict:
        """将数据库行转换为字典"""
        return {
            'id': str(row['id']),
            'user_id': row['user_id'],
            'device_id': row['device_id'],
            'session_id': row['session_id'],
            'start_time': row['start_time'],
            'last_active': row['last_active'],
            'turn_count': row['turn_count'],
            'state': row['state'],
            'emotion': row['emotion'],
            'memory_extracted': row['memory_extracted'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
