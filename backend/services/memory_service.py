import re
import datetime
import json
import math
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from repositories.memory_repo import MemoryRepo
from core.prompt import memory_extract_template
from utils.entity_matcher import AcEntityMatcher


def clean_json_output(output: str) -> str:
    """清理 LLM 返回的 JSON 输出，去除代码块标记
    
    Args:
        output: LLM 返回的原始字符串
        
    Returns:
        清理后的纯 JSON 字符串
    """
    if not output:
        return output
    
    # 去除前后空白
    output = output.strip()
    
    # 匹配并去除 ```json ... ``` 格式
    # 支持带语言标识的代码块和不带语言标识的代码块
    patterns = [
        r'^```json\s*',      # 开头的 ```json
        r'^```\s*',          # 开头的 ```（不带语言）
        r'\s*```$',          # 结尾的 ```
    ]
    
    for pattern in patterns:
        output = re.sub(pattern, '', output, flags=re.MULTILINE)
    
    # 再次去除前后空白
    output = output.strip()
    
    return output

class MemoryService:

    def __init__(self, repo:MemoryRepo, embedding_svc:EmbeddingService,llm_svc:LLMService,logger):
        self.repo = repo
        self.embedding = embedding_svc
        self.llm=llm_svc
        self.logger = logger
    async def fucking(self):
        result=await self.repo.retrieve_memory_in_graph("3f7e4b2c-8a9d-4f1e-9c2b-6a5d4e3f2a1b",['用户','晒太阳'])
        return result

    async def get_memory(self, user_id, device_id, current_text, top_k=5):
        try:
            query_text = current_text

            query_vec = await self.embedding.embed(query_text)

            # 向量检索
            vector_memories = await self.repo.retrieve_memory(user_id, device_id, query_vec, top_k=20)

            # 图检索：先获取所有节点，使用实体匹配器匹配当前文本
            all_nodes = await self.repo.get_all_nodes(user_id)
            
            # 初始化实体匹配器
            matcher = AcEntityMatcher()
            
            # 添加所有节点
            for node_id, node_name in all_nodes:
                matcher.add_node(node_id, node_name)
            
            # 构建自动机
            matcher.build()
            
            # 匹配当前文本中的实体
            matches = matcher.match_unique(current_text)
            
            # 提取匹配到的实体名称列表
            entity_list = [entity_name for _, entity_name in matches]
            
            # 如果没有匹配到实体，默认使用 ["用户"]
            if not entity_list:
                entity_list = ["用户"]
            
            self.logger.info(f"[memory] 实体匹配结果: {entity_list}")
            
            # 调用图检索
            graph_memory = await self.repo.retrieve_memory_in_graph(user_id, entity_list)

            # 提取图检索的记忆ID
            graph_memory_ids = set()
            for memory_item in graph_memory:
                if isinstance(memory_item, dict) and 'memory_id' in memory_item:
                    graph_memory_ids.add(memory_item['memory_id'])

            # 提取向量检索的记忆ID
            vector_memory_ids = {m['id'] for m in vector_memories}

            # 合并去重：保留向量检索和图检索的所有记忆ID
            all_memory_ids = vector_memory_ids.union(graph_memory_ids)

            self.logger.info(f"[memory] 向量检索命中 {len(vector_memory_ids)} 条，图检索命中 {len(graph_memory_ids)} 条，去重后 {len(all_memory_ids)} 条")

            # 根据去重后的ID查询记忆详细信息
            all_memories = []
            if all_memory_ids:
                all_memories = await self.repo.get_memories_by_ids(list(all_memory_ids))

            # 重排序逻辑
            now = datetime.datetime.now(datetime.timezone.utc)
            scored_memories = []

            for memory in all_memories:
                # 计算 recency
                last_used_at = memory.get('last_used_at')
                created_at = memory.get('created_at')
                t = last_used_at or created_at
                if t:
                    delta_days = (now - t).total_seconds() / 86400
                    recency = math.exp(-delta_days / 7)
                else:
                    recency = 0

                # 计算 similarity (从向量检索结果中获取距离)
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

            self.logger.info(f"[memory] 最终命中 {len(top_memories)} 条")

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
            # 渲染模板（模板使用 history 作为变量名）
            prompt = memory_extract_template.render(history=history)
            
            # 调用LLM获取输出
            output = await self.llm.generate(prompt)
            
            # 解析输出（先清理可能的代码块标记）
            try:
                cleaned_output = clean_json_output(output)
                memories = json.loads(cleaned_output)
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

