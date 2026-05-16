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

    async def merge_similar_nodes(self, user_id: str, threshold: float = 0.9) -> int:
        """
        合并相似节点：计算所有节点对之间的相似度，超过阈值则添加边
        
        Args:
            user_id: 用户ID
            threshold: 相似度阈值，默认0.9
        
        Returns:
            新添加的边数量
        """
        try:
            # 获取用户的所有节点
            all_nodes = await self.repo.get_all_nodes(user_id)
            if len(all_nodes) < 2:
                self.logger.info(f"[memory] 用户 {user_id} 节点数量不足，无需合并")
                return 0
            
            self.logger.info(f"[memory] 开始合并相似节点，共 {len(all_nodes)} 个节点")
            
            # 计算每个节点名称的向量
            node_embeddings = {}
            for node_id, node_name in all_nodes:
                embedding = await self.embedding.embed(node_name)
                node_embeddings[node_id] = {
                    'name': node_name,
                    'embedding': embedding
                }
            
            # 获取已存在的边（用于去重）
            existing_edges = await self.repo.get_existing_edges(user_id)
            
            # 枚举所有节点对，计算相似度
            added_count = 0
            node_ids = list(node_embeddings.keys())
            
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    node_id1 = node_ids[i]
                    node_id2 = node_ids[j]
                    
                    # 检查是否已存在边（双向检查）
                    if (node_id1, node_id2) in existing_edges or (node_id2, node_id1) in existing_edges:
                        continue
                    
                    # 计算余弦相似度
                    embedding1 = node_embeddings[node_id1]['embedding']
                    embedding2 = node_embeddings[node_id2]['embedding']
                    
                    similarity = self._cosine_similarity(embedding1, embedding2)
                    
                    # 如果相似度超过阈值，添加边
                    if similarity >= threshold:
                        name1 = node_embeddings[node_id1]['name']
                        name2 = node_embeddings[node_id2]['name']
                        
                        # 在两个方向都添加边（无向图）
                        await self.repo.add_edge_between_nodes(
                            user_id=user_id,
                            source_node_id=node_id1,
                            target_node_id=node_id2,
                            relation_type="similar_to",
                            strength=similarity
                        )
                        await self.repo.add_edge_between_nodes(
                            user_id=user_id,
                            source_node_id=node_id2,
                            target_node_id=node_id1,
                            relation_type="similar_to",
                            strength=similarity
                        )
                        
                        self.logger.info(f"[memory] 节点 '{name1}' 与 '{name2}' 相似度 {similarity:.4f}，已添加边")
                        added_count += 1
            
            self.logger.info(f"[memory] 相似节点合并完成，共添加 {added_count} 条边")
            return added_count
        
        except Exception as e:
            self.logger.error(f"[memory] 合并相似节点失败: {e}")
            return 0

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        计算两个向量之间的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
        
        Returns:
            余弦相似度（0-1）
        """
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

