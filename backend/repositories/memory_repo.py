from datetime import datetime, timezone
import json
import uuid

from arrow import utcnow
import asyncpg

class MemoryRepo:
    def __init__(self, db_pool:asyncpg.Pool,logger):
        self.db = db_pool
        self.logger=logger
        
    async def save_memory(self, user_id: str, device_id: str, memory_data: dict, embedding: list[float]):
        """保存提取的记忆
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            memory_data: 记忆数据
            embedding: 向量嵌入
        """
        query = """
        INSERT INTO memories(
            id, user_id, device_id,
            content, type,
            source_memory_ids, tags,
            embedding,
            emotion, emotion_intensity,
            importance,
            created_at, last_used_at,
            access_count,
            is_active
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
        """
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                str(uuid.uuid4()),
                user_id,
                device_id,
                memory_data.get("content"),
                memory_data.get("type", "event"),
                memory_data.get("source_memory_ids"),
                memory_data.get("tags"),
                self._to_pgvector(embedding),
                memory_data.get("emotion"),
                memory_data.get("emotion_intensity", 0.5),
                memory_data.get("importance", 0.5),
                self._now(),
                None,
                0,
                True
            )
        self.logger.info(f"[MemoryRepo] 保存记忆成功: {memory_data.get('content')}")

    async def retrieve_memory(self, user_id: str, device_id: str, embedding: list[float], top_k: int = 5):
        """根据向量检索记忆
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            embedding: 向量
            top_k: 返回的记忆数量
            
        Returns:
            记忆列表
        """
        query = """
        SELECT 
            id, user_id, device_id, content, type, 
            source_memory_ids, tags, emotion, emotion_intensity, 
            importance, created_at, last_used_at, access_count,
            embedding <-> $3 AS distance
        FROM memories
        WHERE user_id = $1 AND device_id = $2 AND is_active = true
        ORDER BY embedding <-> $3
        LIMIT $4
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                query, 
                user_id, 
                device_id, 
                self._to_pgvector(embedding), 
                top_k
            )
            # 转换为字典列表
            memories = []
            for row in rows:
                memory_dict = dict(row)
                # 处理JSONB字段
                if memory_dict.get('source_memory_ids'):
                    memory_dict['source_memory_ids'] = json.loads(memory_dict['source_memory_ids'])
                if memory_dict.get('tags'):
                    memory_dict['tags'] = json.loads(memory_dict['tags'])
                memories.append(memory_dict)
            
            self.logger.info(f"[MemoryRepo] 检索到 {len(memories)} 条记忆")
            return memories

    async def update_access(self, memory_ids: list[str]):
        """更新记忆访问次数和最后使用时间

        Args:
            memory_ids: 记忆ID列表

        """
        if not memory_ids:
            return

        # 验证 UUID 格式
        valid_ids = []
        for memory_id in memory_ids:
            try:
                # 验证 UUID 格式
                uuid.UUID(memory_id)
                valid_ids.append(memory_id)
            except ValueError:
                self.logger.warning(f"无效的记忆ID格式: {memory_id}")

        if not valid_ids:
            return

        query = """
        UPDATE memories
        SET access_count = access_count + 1,
            last_used_at = $2
        WHERE id = ANY($1::uuid[])
        """
        async with self.db.acquire() as conn:
            await conn.execute(query, valid_ids, datetime.now(timezone.utc))
        self.logger.info(f"[MemoryRepo] 更新访问次数: {len(valid_ids)} 条")
    def _parse_event_time(self,s):
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()
    def _now(self):
        return datetime.now(timezone.utc)
    def _to_pgvector(self,vec: list[float]) -> str:
        return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
