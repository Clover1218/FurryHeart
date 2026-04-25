import asyncpg
from typing import List, Dict, Any


class ConfigRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_all_schema(self) -> List[Dict[str, Any]]:
        """获取所有配置 schema"""
        query = """
        SELECT key, type, default_value, options, description
        FROM config_schema
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [{
                'key': row['key'],
                'type': row['type'],
                'default_value': row['default_value'],
                'options': row['options'],
                'description': row['description']
            } for row in rows]

    async def get_all_system_configs(self) -> Dict[str, Any]:
        """获取所有系统配置"""
        query = """
        SELECT key, value
        FROM system_config
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return {row['key']: row['value'] for row in rows}

    async def get_all_user_configs(self, user_id: str) -> Dict[str, Any]:
        """获取指定用户的所有配置"""
        query = """
        SELECT key, value
        FROM user_config
        WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            return {row['key']: row['value'] for row in rows}

    async def batch_upsert_user_config(self, user_id: str, updates: Dict[str, Any]):
        """批量更新或插入用户配置"""
        query = """
        INSERT INTO user_config (user_id, key, value, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id, key)
        DO UPDATE SET
            value = $3,
            updated_at = NOW()
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for key, value in updates.items():
                    await conn.execute(query, user_id, key, value)
