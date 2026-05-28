from datetime import datetime, timezone
import json
import uuid

import asyncpg


class MemoryRepo:
    def __init__(self, db_pool: asyncpg.Pool, logger):
        self.db = db_pool
        self.logger = logger

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
            is_active,
            emotion_confidence
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        )
        """
        memory_id = str(uuid.uuid4())
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                memory_id,
                user_id,
                device_id,
                memory_data.get("content"),
                memory_data.get("type", "event"),
                json.dumps(memory_data.get("source_memory_ids")) if memory_data.get("source_memory_ids") else None,
                json.dumps(memory_data.get("tags")) if memory_data.get("tags") else None,
                self._to_pgvector(embedding),
                memory_data.get("emotion"),
                memory_data.get("emotion_intensity", 0.5),
                memory_data.get("importance", 0.5),
                self._now(),
                None,
                0,
                True,
                memory_data.get("emotion_confidence", 0.5)
            )

            # 处理三元组，创建知识图谱节点和边
            triples = memory_data.get("triples", [])
            importance = memory_data.get("importance", 0.5)
            for triple in triples:
                subj = triple.get("subject", "").strip()
                pred = triple.get("predicate", "").strip()
                obj = triple.get("object", "").strip()
                if not subj or not pred or not obj:
                    continue  # 跳过无效三元组

                # 获取或创建节点（subject 和 object），并将当前记忆ID挂载到节点上
                subj_node_id = await self._get_or_create_node(
                    conn, user_id, subj, "entity", memory_ids=[memory_id]
                )
                obj_node_id = await self._get_or_create_node(
                    conn, user_id, obj, "entity", memory_ids=[memory_id]
                )
                # 创建边（不再挂载记忆）
                await self._create_or_update_edge(
                    conn,
                    source_node_id=subj_node_id,
                    target_node_id=obj_node_id,
                    relation_type=pred,
                    strength=importance
                )

        self.logger.info(f"[MemoryRepo] 保存记忆成功: {memory_data.get('content')}")

    async def _get_or_create_node(self, conn: asyncpg.Connection, user_id: str, name: str, node_type: str, properties: dict = None, memory_ids: list = None) -> str:
        """
        获取或创建知识节点。
        返回 node_id (字符串形式的 UUID)
        
        Args:
            conn: 数据库连接
            user_id: 用户ID
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            memory_ids: 要挂载到节点的记忆ID列表
        """
        if properties is None:
            properties = {}
        if memory_ids is None:
            memory_ids = []

        # 尝试查找已有节点（同一用户下同名同类型）
        query = """
        SELECT id, memory_items FROM memory_nodes
        WHERE user_id = $1 AND name = $2 AND type = $3
        LIMIT 1
        """
        row = await conn.fetchrow(query, user_id, name, node_type)
        if row:
            node_id = str(row['id'])
            # 如果有记忆需要挂载，更新节点
            if memory_ids:
                await self._add_memory_to_node(conn, node_id, memory_ids)
            return node_id

        # 不存在则插入
        node_id = str(uuid.uuid4())
        # 准备 memory_items 字段
        memory_items = [{"memory_id": mid, "added_at": datetime.now(timezone.utc).isoformat()} for mid in memory_ids]
        insert_query = """
        INSERT INTO memory_nodes (id, user_id, name, type, properties, memory_items)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        await conn.execute(insert_query, node_id, user_id, name, node_type, json.dumps(properties), json.dumps(memory_items))
        return node_id

    async def _add_memory_to_node(self, conn: asyncpg.Connection, node_id: str, memory_ids: list):
        """
        向节点添加记忆ID
        
        Args:
            conn: 数据库连接
            node_id: 节点ID
            memory_ids: 记忆ID列表
        """
        if not memory_ids:
            return

        # 获取当前节点的 memory_items
        query = """
        SELECT memory_items FROM memory_nodes WHERE id = $1
        """
        row = await conn.fetchrow(query, node_id)
        if not row:
            return

        current_items = row['memory_items']
        if current_items:
            try:
                memory_items = json.loads(current_items)
            except:
                memory_items = []
        else:
            memory_items = []

        # 合并新的记忆ID（去重）
        existing_ids = {item['memory_id'] for item in memory_items if isinstance(item, dict) and 'memory_id' in item}
        for mid in memory_ids:
            if mid not in existing_ids:
                memory_items.append({
                    "memory_id": mid,
                    "added_at": datetime.now(timezone.utc).isoformat()
                })
                existing_ids.add(mid)

        # 更新节点
        update_query = """
        UPDATE memory_nodes
        SET memory_items = $1, updated_at = NOW()
        WHERE id = $2
        """
        await conn.execute(update_query, json.dumps(memory_items), node_id)

    async def _create_or_update_edge(self, conn: asyncpg.Connection, source_node_id: str, target_node_id: str,
                                     relation_type: str, strength: float = 0.5, properties: dict = None):
        """
        创建或更新关系边。
        - 如果相同 (source, target, relation_type) 已存在，则更新 strength 和 properties。
        - 记忆挂载到节点上，不再挂载到边上。
        """
        if properties is None:
            properties = {}

        # 尝试更新
        update_query = """
        UPDATE memory_edges
        SET strength = $1,
            properties = $2,
            updated_at = NOW()
        WHERE source_node_id = $3
          AND target_node_id = $4
          AND relation_type = $5
        RETURNING id
        """
        row = await conn.fetchrow(update_query, strength, json.dumps(properties), source_node_id, target_node_id, relation_type)
        if row:
            return str(row['id'])

        # 不存在则插入
        edge_id = str(uuid.uuid4())
        insert_query = """
        INSERT INTO memory_edges (id, source_node_id, target_node_id, relation_type, strength, properties)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        await conn.execute(insert_query, edge_id, source_node_id, target_node_id, relation_type, strength, json.dumps(properties))
        return edge_id

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
            is_active, emotion_confidence,
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
                # 将 UUID 转换为字符串
                if 'id' in memory_dict:
                    memory_dict['id'] = str(memory_dict['id'])
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

    async def get_user_memories(self, user_id: str, device_id: str = "") -> list[dict]:
        """获取用户的所有记忆

        Args:
            user_id: 用户ID
            device_id: 设备ID（可选）

        Returns:
            记忆列表，包含 id 和 content
        """
        query = """
        SELECT 
            id, content, type, emotion, created_at
        FROM memories
        WHERE user_id = $1 
        AND (device_id = $2 OR $2 = '')
        AND is_active = true
        ORDER BY created_at DESC
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id, device_id)

            memories = []
            for row in rows:
                memory_dict = {
                    'id': str(row['id']),
                    'content': row['content'],
                    'type': row['type'],
                    'emotion': row['emotion'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                memories.append(memory_dict)

            self.logger.info(f"[MemoryRepo] 获取用户 {user_id} 的记忆列表: {len(memories)} 条")
            return memories

    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict]:
        """根据记忆ID列表批量获取记忆详情

        Args:
            memory_ids: 记忆ID列表

        Returns:
            记忆列表
        """
        if not memory_ids:
            return []

        # 验证 UUID 格式
        valid_ids = []
        for memory_id in memory_ids:
            try:
                uuid.UUID(memory_id)
                valid_ids.append(memory_id)
            except ValueError:
                self.logger.warning(f"无效的记忆ID格式: {memory_id}")

        if not valid_ids:
            return []

        placeholders = ','.join([f'${i+1}' for i in range(len(valid_ids))])
        query = f"""
        SELECT 
            id, user_id, device_id, content, type, 
            source_memory_ids, tags, emotion, emotion_intensity, 
            importance, created_at, last_used_at, access_count,
            is_active, emotion_confidence
        FROM memories
        WHERE id IN ({placeholders}) AND is_active = true
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *valid_ids)

            memories = []
            for row in rows:
                memory_dict = dict(row)
                if 'id' in memory_dict:
                    memory_dict['id'] = str(memory_dict['id'])
                if memory_dict.get('source_memory_ids'):
                    memory_dict['source_memory_ids'] = json.loads(memory_dict['source_memory_ids'])
                if memory_dict.get('tags'):
                    memory_dict['tags'] = json.loads(memory_dict['tags'])
                memories.append(memory_dict)

            self.logger.info(f"[MemoryRepo] 根据ID列表获取 {len(memories)} 条记忆")
            return memories

    async def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆（软删除）

        Args:
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        query = """
        UPDATE memories
        SET is_active = false
        WHERE id = $1 AND is_active = true
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, memory_id)

            # 检查是否有行被更新
            if result == "UPDATE 0":
                self.logger.warning(f"[MemoryRepo] 记忆 {memory_id} 不存在或已被删除")
                return False

            self.logger.info(f"[MemoryRepo] 成功删除记忆: {memory_id}")
            return True

    async def get_node(self, node_id: str) -> dict:
        """获取指定节点

        Args:
            node_id: 节点ID

        Returns:
            节点信息
        """
        query = """
        SELECT id, user_id, name, type, properties, memory_items, created_at, updated_at
        FROM memory_nodes
        WHERE id = $1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, node_id)
            if not row:
                return None

            node_dict = {
                'id': str(row['id']),
                'user_id': row['user_id'],
                'name': row['name'],
                'type': row['type'],
                'properties': json.loads(row['properties']) if row['properties'] else {},
                'memory_items': json.loads(row['memory_items']) if row['memory_items'] else [],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            return node_dict

    async def get_user_nodes(self, user_id: str) -> list[dict]:
        """获取用户的所有节点

        Args:
            user_id: 用户ID

        Returns:
            节点列表
        """
        query = """
        SELECT id, name, type, properties, memory_items, created_at
        FROM memory_nodes
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)

            nodes = []
            for row in rows:
                node_dict = {
                    'id': str(row['id']),
                    'name': row['name'],
                    'type': row['type'],
                    'properties': json.loads(row['properties']) if row['properties'] else {},
                    'memory_items': json.loads(row['memory_items']) if row['memory_items'] else [],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                nodes.append(node_dict)

            self.logger.info(f"[MemoryRepo] 获取用户 {user_id} 的节点列表: {len(nodes)} 条")
            return nodes

    async def create_node(self, user_id: str, name: str, node_type: str, properties: dict = None, memory_items: list = None) -> str:
        """创建新节点

        Args:
            user_id: 用户ID
            name: 节点名称
            node_type: 节点类型
            properties: 节点属性
            memory_items: 挂载的记忆列表

        Returns:
            创建的节点ID
        """
        if properties is None:
            properties = {}
        if memory_items is None:
            memory_items = []

        node_id = str(uuid.uuid4())
        query = """
        INSERT INTO memory_nodes (id, user_id, name, type, properties, memory_items)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        async with self.db.acquire() as conn:
            await conn.execute(query, node_id, user_id, name, node_type, json.dumps(properties), json.dumps(memory_items))

        self.logger.info(f"[MemoryRepo] 创建节点成功: {name} ({node_type})")
        return node_id

    async def update_node(self, node_id: str, name: str = None, node_type: str = None, properties: dict = None, memory_items: list = None) -> bool:
        """更新节点信息

        Args:
            node_id: 节点ID
            name: 新名称（可选）
            node_type: 新类型（可选）
            properties: 新属性（可选）
            memory_items: 新的记忆列表（可选）

        Returns:
            是否更新成功
        """
        # 构建更新字段
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if node_type is not None:
            updates.append(f"type = ${param_count}")
            params.append(node_type)
            param_count += 1

        if properties is not None:
            updates.append(f"properties = ${param_count}")
            params.append(json.dumps(properties))
            param_count += 1

        if memory_items is not None:
            updates.append(f"memory_items = ${param_count}")
            params.append(json.dumps(memory_items))
            param_count += 1

        updates.append(f"updated_at = NOW()")
        params.append(node_id)

        if not updates:
            return False

        query = f"""
        UPDATE memory_nodes
        SET {', '.join(updates)}
        WHERE id = ${param_count}
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, *params)

            if result == "UPDATE 0":
                self.logger.warning(f"[MemoryRepo] 节点 {node_id} 不存在")
                return False

            self.logger.info(f"[MemoryRepo] 更新节点成功: {node_id}")
            return True

    async def delete_node(self, node_id: str) -> bool:
        """删除节点（级联删除相关边）

        Args:
            node_id: 节点ID

        Returns:
            是否删除成功
        """
        query = """
        DELETE FROM memory_nodes
        WHERE id = $1
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, node_id)

            if result == "DELETE 0":
                self.logger.warning(f"[MemoryRepo] 节点 {node_id} 不存在")
                return False

            self.logger.info(f"[MemoryRepo] 删除节点成功: {node_id}")
            return True

    async def get_edge(self, edge_id: str) -> dict:
        """获取指定边

        Args:
            edge_id: 边ID

        Returns:
            边信息
        """
        query = """
        SELECT id, source_node_id, target_node_id, relation_type, strength, properties, created_at, updated_at
        FROM memory_edges
        WHERE id = $1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, edge_id)
            if not row:
                return None

            edge_dict = {
                'id': str(row['id']),
                'source_node_id': str(row['source_node_id']),
                'target_node_id': str(row['target_node_id']),
                'relation_type': row['relation_type'],
                'strength': row['strength'],
                'properties': json.loads(row['properties']) if row['properties'] else {},
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            return edge_dict

    async def get_user_edges(self, user_id: str) -> list[dict]:
        """获取用户的所有边

        Args:
            user_id: 用户ID

        Returns:
            边列表
        """
        query = """
        SELECT e.id, e.source_node_id, e.target_node_id, e.relation_type, e.strength, e.properties, e.created_at,
               s.name as source_name, t.name as target_name
        FROM memory_edges e
        JOIN memory_nodes s ON e.source_node_id = s.id
        JOIN memory_nodes t ON e.target_node_id = t.id
        WHERE s.user_id = $1
        ORDER BY e.created_at DESC
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)

            edges = []
            for row in rows:
                edge_dict = {
                    'id': str(row['id']),
                    'source_node_id': str(row['source_node_id']),
                    'target_node_id': str(row['target_node_id']),
                    'source_name': row['source_name'],
                    'target_name': row['target_name'],
                    'relation_type': row['relation_type'],
                    'strength': row['strength'],
                    'properties': json.loads(row['properties']) if row['properties'] else {},
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                edges.append(edge_dict)

            return edges

    async def get_user_graph(self, user_id: str) -> dict:
        """获取用户的完整知识图谱数据（节点+边+记忆）

        Args:
            user_id: 用户ID

        Returns:
            图数据，格式如下：
            {
                "nodes": [
                    {
                        "id": "node_id",
                        "label": "节点名称",
                        "type": "节点类型",
                        "memories": [
                            {
                                "id": "memory_id",
                                "content": "记忆内容",
                                "emotion": "情感类型",
                                "importance": 重要性分数
                            }
                        ]
                    }
                ],
                "edges": [
                    {
                        "source": "源节点ID",
                        "target": "目标节点ID",
                        "relation": "关系类型"
                    }
                ]
            }
        """
        # 获取所有节点
        nodes = await self.get_user_nodes(user_id)
        
        # 获取所有边
        edges = await self.get_user_edges(user_id)
        
        # 获取所有记忆详情（用于填充节点的memory_items）
        memory_ids = []
        for node in nodes:
            memory_items = node.get('memory_items', [])
            for item in memory_items:
                if isinstance(item, dict) and 'memory_id' in item:
                    memory_ids.append(item['memory_id'])
                elif isinstance(item, str):
                    memory_ids.append(item)
        
        # 获取记忆详情
        memory_details = {}
        if memory_ids:
            placeholders = ','.join([f'${i+1}' for i in range(len(memory_ids))])
            query = f"""
            SELECT id, content, emotion, importance
            FROM memories
            WHERE id IN ({placeholders}) AND is_active = true
            """
            async with self.db.acquire() as conn:
                rows = await conn.fetch(query, *memory_ids)
                for row in rows:
                    memory_details[str(row['id'])] = {
                        'id': str(row['id']),
                        'content': row['content'],
                        'emotion': row['emotion'],
                        'importance': row['importance']
                    }
        
        # 构建前端需要的节点格式
        result_nodes = []
        for node in nodes:
            node_memories = []
            memory_items = node.get('memory_items', [])
            for item in memory_items:
                if isinstance(item, dict) and 'memory_id' in item:
                    mem_id = item['memory_id']
                elif isinstance(item, str):
                    mem_id = item
                else:
                    continue
                
                if mem_id in memory_details:
                    node_memories.append(memory_details[mem_id])
            
            result_nodes.append({
                'id': node['id'],
                'label': node['name'],
                'type': node['type'],
                'memories': node_memories
            })
        
        # 构建前端需要的边格式
        result_edges = []
        for edge in edges:
            result_edges.append({
                'source': edge['source_node_id'],
                'target': edge['target_node_id'],
                'relation': edge['relation_type']
            })
        
        return {
            'nodes': result_nodes,
            'edges': result_edges
        }

    async def delete_edge(self, edge_id: str) -> bool:
        """删除边

        Args:
            edge_id: 边ID

        Returns:
            是否删除成功
        """
        query = """
        DELETE FROM memory_edges
        WHERE id = $1
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, edge_id)

            if result == "DELETE 0":
                self.logger.warning(f"[MemoryRepo] 边 {edge_id} 不存在")
                return False

            self.logger.info(f"[MemoryRepo] 删除边成功: {edge_id}")
            return True

    async def retrieve_memory_in_graph(self,user_id:str,entity_list:list[str]):
        node_id=await self._get_memory_node_id(user_id,entity_list)
        memory_id_list=await self._spreading_activation(user_id,node_id)
        result=await self._get_memories_from_nodes(memory_id_list)
        return result

    async def _spreading_activation(self,user_id:str,node_list,max_depth: int = 2,
        decay: float = 0.7,
        min_strength: float = 0.3):
        seed_strs = [str(nid) for nid in node_list]
        
        query = """
        WITH RECURSIVE activation AS (
            SELECT 
                id AS node_id,
                1.0::double precision AS energy,
                0 AS depth
            FROM memory_nodes
            WHERE id = ANY($1::uuid[])

            UNION ALL

            SELECT 
                e.target_node_id,
                a.energy * (e.strength * $2) AS energy,
                a.depth + 1
            FROM activation a
            JOIN memory_edges e ON e.source_node_id = a.node_id
            WHERE a.depth < $3
              AND e.strength >= $4
              AND (a.energy * e.strength) > 0.05
        )
        SELECT 
            node_id,
            SUM(energy) AS total_energy
        FROM activation
        GROUP BY node_id
        ORDER BY total_energy DESC;
        """

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, seed_strs, decay, max_depth, min_strength)
            return {row['node_id']: row['total_energy'] for row in rows}


        pass
    
    async def _get_memories_from_nodes(self,node_scores,
                                      limit_per_node: int = 3,max_total: int = 10):
        if not node_scores:
            return []

        node_ids = list(node_scores.keys())
        async with self.db.acquire() as conn:
            # 获取节点的 memory_items
            rows = await conn.fetch(
                "SELECT id, memory_items FROM memory_nodes WHERE id = ANY($1::uuid[])",
                [str(nid) for nid in node_ids]
            )

            # 收集记忆ID及其来源节点能量
            memory_candidates = {}
            for row in rows:
                node_id = row['id']
                energy = node_scores.get(node_id, 0.0)
                memory_items = row['memory_items']
                if not memory_items:
                    continue
                # memory_items 可能是 JSON 字符串或已解析的列表
                if isinstance(memory_items, str):
                    memory_items = json.loads(memory_items)
                for item in memory_items:
                    if isinstance(item, dict) and 'memory_id' in item:
                        mem_id = item['memory_id']
                        if mem_id not in memory_candidates:
                            memory_candidates[mem_id] = []
                        memory_candidates[mem_id].append(energy)
                    elif isinstance(item, str):
                        # 兼容旧格式：直接存储 ID 字符串
                        mem_id = item
                        if mem_id not in memory_candidates:
                            memory_candidates[mem_id] = []
                        memory_candidates[mem_id].append(energy)

            if not memory_candidates:
                return []

            # 计算每个记忆的最终得分（累加能量）
            mem_scores = {mem_id: sum(energies) for mem_id, energies in memory_candidates.items()}

            # 批量获取记忆详情
            mem_ids = list(mem_scores.keys())
            placeholders = ','.join([f'${i+1}' for i in range(len(mem_ids))])
            query = f"""
                SELECT id, content, importance, emotion
                FROM memories
                WHERE id IN ({placeholders}) AND is_active = true
            """
            mem_rows = await conn.fetch(query, *mem_ids)

            result = []
            for row in mem_rows:
                mem_id = str(row['id'])
                score = mem_scores.get(mem_id, 0.0)
                result.append({
                    "memory_id": mem_id,
                    "content": row['content'],
                    "importance": row['importance'],
                    "emotion": row['emotion'],
                    "score": score
                })

            result.sort(key=lambda x: x['score'], reverse=True)
            return result[:max_total]

    async def _get_memory_node_id(self,user_id:str,entity_list:list[str]):
        if len(entity_list)<=0:
            return []
        placeholders = ','.join([f'${i+2}' for i in range(len(entity_list))])
        print(placeholders)
        query = f"""
            SELECT DISTINCT id, name FROM memory_nodes
            WHERE user_id = $1 AND name IN ({placeholders})
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id,*entity_list)
        exact = {row['name']: row['id'] for row in rows}
        print(exact)
        return list(exact.values())

    def _parse_event_time(self, s):
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _now(self):
        return datetime.now(timezone.utc)

    def _to_pgvector(self, vec: list[float]) -> str:
        return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    async def get_all_nodes(self, user_id: str) -> list[tuple[str, str]]:
        """获取用户的所有节点（node_id, node_name）"""
        query = """
        SELECT id, name 
        FROM memory_nodes 
        WHERE user_id = $1
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)
        
        return [(str(row['id']), row['name']) for row in rows]

    async def add_edge_between_nodes(self, user_id: str, source_node_id: str, target_node_id: str, relation_type: str = "similar_to", strength: float = 1.0) -> str:
        """
        在两个节点之间添加边
        
        Args:
            user_id: 用户ID
            source_node_id: 源节点ID
            target_node_id: 目标节点ID
            relation_type: 关系类型，默认为 "similar_to"
            strength: 关系强度
        
        Returns:
            创建的边ID
        """
        async with self.db.acquire() as conn:
            edge_id = await self._create_or_update_edge(
                conn,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                relation_type=relation_type,
                strength=strength
            )
        
        self.logger.info(f"[MemoryRepo] 在节点 {source_node_id} 和 {target_node_id} 之间创建边: {relation_type}")
        return edge_id

    async def get_existing_edges(self, user_id: str) -> set[tuple[str, str]]:
        """
        获取用户已存在的所有边（用于去重）
        
        Args:
            user_id: 用户ID
        
        Returns:
            边的集合，每条边表示为 (source_node_id, target_node_id)
        """
        query = """
        SELECT source_node_id, target_node_id
        FROM memory_edges e
        JOIN memory_nodes s ON e.source_node_id = s.id
        WHERE s.user_id = $1
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)
        
        return {(str(row['source_node_id']), str(row['target_node_id'])) for row in rows}
