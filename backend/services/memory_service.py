import re
import datetime
import json
import math
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from repositories.memory_repo import MemoryRepo
from core.prompt import memory_extract_template

class MemoryService:

    def __init__(self, repo:MemoryRepo, embedding_svc:EmbeddingService,llm_svc:LLMService,logger):
        self.repo = repo
        self.embedding = embedding_svc
        self.llm=llm_svc
        self.logger = logger

    async def get_memory(self, user_id, device_id, current_text, top_k=5):
        try:
            query_text = current_text

            query_vec = await self.embedding.embed(query_text)

            memories = await self.repo.retrieve_memory(user_id, device_id, query_vec, top_k=20)

            # 重排序逻辑
            now = datetime.datetime.utcnow()
            scored_memories = []

            for memory in memories:
                # 计算 recency
                last_used_at = memory.get('last_used_at')
                created_at = memory.get('created_at')
                t = last_used_at or created_at
                if t:
                    delta_days = (now - t).total_seconds() / 86400
                    recency = math.exp(-delta_days / 7)
                else:
                    recency = 0

                # 计算 similarity (假设 memory 中有 distance 字段)
                distance = memory.get('distance', 0)
                similarity = 1 - distance

                # 获取 importance
                importance = memory.get('importance', 0.5)

                # 过滤低质量记忆
                if importance < 0.4:
                    continue

                # 计算最终分数
                score = (
                    0.45 * similarity +
                    0.30 * importance +
                    0.25 * recency
                )

                scored_memories.append((memory, score))

            # 按分数排序
            scored_memories.sort(key=lambda x: x[1], reverse=True)

            # 取前 top_k 条
            top_memories = [m for m, _ in scored_memories[:top_k]]

            # 更新访问统计
            memory_ids = [m['id'] for m in top_memories]
            await self.repo.update_access(memory_ids)

            self.logger.info(f"[memory] 命中 {len(top_memories)} 条")

            return top_memories

        except Exception as e:
            self.logger.error(f"[memory] 检索失败: {e}")
            return []

    async def extract_memory(self, user_id: str, device_id: str, history: str):
        """提取记忆
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            history: 对话历史
            
        Returns:
            提取的记忆数量
        """
        try:
            # 渲染模板
            prompt = memory_extract_template.render(input=history)
            
            # 调用LLM获取输出
            output = await self.llm.generate(prompt)
            
            # 解析输出
            try:
                memories = json.loads(output)
            except json.JSONDecodeError:
                self.logger.error(f"[memory] 解析记忆输出失败: {output}")
                return 0
            
            # 处理提取的记忆
            count = 0
            for memory_data in memories:
                # 验证必要字段
                if "content" not in memory_data:
                    continue
                
                # 生成embedding
                embedding = await self.embedding.embed(memory_data["content"])
                
                # 保存到数据库
                await self.repo.save_memory(
                    user_id=user_id,
                    device_id=device_id,
                    memory_data=memory_data,
                    embedding=embedding
                )
                count += 1
            
            self.logger.info(f"[memory] 提取并保存了 {count} 条记忆")
            return count
            
        except Exception as e:
            self.logger.error(f"[memory] 提取记忆失败: {e}")
            return 0

