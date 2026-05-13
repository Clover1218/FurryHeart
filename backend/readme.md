# FurryHeart Backend

绒绒心语项目的后端服务，采用 Python + FastAPI 开发，遵循 PEP 8 命名规范。

## 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [数据库设计](#数据库设计)
- [架构说明](#架构说明)
- [核心模块](#核心模块)
- [设计理念](#设计理念)

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.10+ |
| 框架 | FastAPI | 0.104.1 |
| 数据库 | PostgreSQL | 15+ |
| 缓存 | Redis | 5.0.1 |
| 数据验证 | Pydantic | 2.5.2 |
| 向量化 | Sentence-Transformers | 2.2.2 |
| LLM | OpenAI API (兼容) | 1.13.3 |
| 提示词模板引擎 | Jinja2 | 3.1.2 |

## 项目结构

```
backend/
├── api/                    # API 路由层
│   ├── __init__.py
│   ├── auth_api.py         # 认证接口
│   ├── chat_api.py         # 聊天接口
│   ├── config_api.py       # 配置接口
│   ├── device_api.py       # 设备接口
│   ├── user_api.py         # 用户接口
│   └── ws_api.py           # WebSocket 接口
├── core/                   # 核心基础设施
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── db.py              # 数据库连接池
│   ├── exceptions.py      # 异常定义
│   ├── logger.py          # 日志配置
│   ├── prompt.py          # 提示词模板
│   └── ws_manager.py      # WebSocket 管理器
├── models/                # 数据模型
│   ├── __init__.py
│   ├── auth_model.py
│   ├── device_model.py
│   └── user_model.py
├── orchestrator/          # 业务编排层
│   ├── __init__.py
│   └── chat_orchestator.py
├── repositories/          # 数据访问层 (Repository)
│   ├── __init__.py
│   ├── auth_repo.py
│   ├── config_repo.py
│   ├── device_repo.py
│   ├── history_models.py
│   ├── history_repo.py
│   ├── memory_repo.py
│   ├── session_repo.py
│   ├── user_models.py
│   └── user_repo.py
├── schemas/               # 请求/响应 Schema
│   ├── __init__.py
│   ├── auth_schema.py
│   └── base_response.py
├── services/              # 业务服务层
│   ├── __init__.py
│   ├── auth_service.py
│   ├── config_service.py
│   ├── device_service.py
│   ├── embedding_service.py
│   ├── emotion_service.py
│   ├── history_service.py
│   ├── llm_service.py
│   ├── memory_service.py
│   ├── scene_service.py
│   ├── session_service.py
│   ├── user_service.py
│   ├── ws_service.py
│   └── llm/              # LLM 客户端
│       ├── deepseek_client.py
│       └── iflow_client.py
├── utils/                 # 工具函数
│   ├── __init__.py
│   ├── entity_matcher.py   # 实体匹配器 (Aho-Corasick)
│   ├── request.py
│   └── snowflake.py
├── logs/                  # 日志目录
├── .env.example          # 环境变量示例
├── requirements.txt      # 依赖清单
├── main.py              # 应用入口
└── readme.md            # 本文档
```

## 快速开始

### 前期准备
确保已安装：
- Python 3.10+
- PostgreSQL 15+
- pgvector 扩展

### 安装依赖

```powershell
cd backend
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env`，并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env

```

### 4. 初始化数据库

首先创建数据库并安装扩展：

```sql
CREATE DATABASE <你的数据表名字>;
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. 启动服务

```powershell
# 开发模式
python run.py

# 或者使用 uvicorn 直接启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
### 6. 访问 API 文档

服务启动后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 配置说明

### 提示词配置

提示词模板定义在 `core/prompt.py` 中，包括：

- `base_chat_template`: 基础聊天模板
- `memory_extract_template`: 记忆提取模板
- `entity_extract_template`: 实体提取模板

场景提示词和基础人设提示词在数据表system_config中

## API 接口

### 统一响应格式

所有接口返回统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| 状态码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

### 认证接口 (Auth)

#### POST /api/auth/wx_login

**说明**：通过微信登录凭证换取用户认证令牌与用户ID

**请求**：
```json
{
  "code": "wx1165156"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "afaea2-faf32ga-adwd",
    "is_new_user": true,
    "user_id": "4949116489"
  }
}
```

### 聊天接口 (Chat)

#### POST /api/chat

**说明**：发送对话消息

**请求头**：`Authorization: Bearer <token>`

**请求体**：
```json
{
  "input": "你好，我今天心情不太好"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "reply": "发生什么事了吗？愿意和我说说吗？",
    "debug_info": "xxx"
  }
}
```

#### GET /api/chat/history

**说明**：获取聊天历史记录

**请求参数**：
- `cursor`: 分页游标（可选）
- `limit`: 每页条数，默认20

**响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "messages": [
      {
        "id": "uuid",
        "role": "user",
        "content": "你好",
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": "uuid",
        "role": "assistant",
        "content": "你好！",
        "created_at": "2024-01-01T00:00:01Z"
      }
    ],
    "next_cursor": "2024-01-01T00:00:00Z"
  }
}
```

#### GET /api/chat/clear

**说明**：清除用户的所有聊天记录

**响应**：
```json
{
  "code": 0,
  "message": "聊天记录清除成功",
  "data": {
    "success": true
  }
}
```

#### POST /api/chat/update_memory

**说明**：强制提取用户记忆

**响应**：
```json
{
  "code": 0,
  "message": "记忆提取成功",
  "data": {
    "count": 5
  }
}
```



#### GET /api/chat/memory/graph

**说明**：获取用户的记忆图谱数据

**响应**：
```json
{
  "code": 0,
  "message": "获取成功",
  "data": {
    "nodes": [
      {
        "id": "node-id",
        "label": "实体名称",
        "type": "person",
        "memories": [...]
      }
    ],
    "edges": [
      {
        "source": "node-id-1",
        "target": "node-id-2",
        "relation": "朋友"
      }
    ]
  }
}
```

#### POST /api/chat/memory/delete

**说明**：删除指定记忆

**请求体**：
```json
{
  "memory_id": "uuid"
}
```

### WebSocket 接口

#### 连接地址

```
ws://localhost:8000/ws/{user_id}
```

## 数据库设计

### 核心表结构

#### sessions 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | TEXT | 用户ID |
| device_id | TEXT | 设备ID |
| state | TEXT | 会话状态 (STARTING/CHATTING/ENDED) |
| turn_count | INT | 对话轮数 |
| emotion | TEXT | 当前session用户情绪 |
| memory_extracted | BOOLEAN | 是否已提取记忆 |
| start_time | TIMESTAMPTZ | 开始时间 |
| last_active | TIMESTAMPTZ | 最后活跃时间 |
| created_at | TIMESTAMPTZ | 创建时间(与start_time重复，考虑删除) |
| updated_at | TIMESTAMPTZ | 上一次更新时间 |


#### memories 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | TEXT | 用户ID |
| device_id | TEXT | 设备ID |
| content | VARCHAR(255) | 记忆内容 |
| type | TEXT | 记忆类型 (event/insight) |
| emotion | TEXT | 情感标签 |
| emotion_intensity | FLOAT8 | 情感烈度 |
| emotion_confidence | FLOAT8 | 情感置信度 |
| importance | FLOAT | 重要性 (0-1) |
| embedding | VECTOR(384) | 向量嵌入 |
| source_memory_ids | JSONB | 来源记忆ID列表(保留作反思) |
| tags | JSONB | 标签列表 |
| is_active | BOOLEAN | 是否活跃 |
| created_at | TIMESTAMP | 创建时间 |
| last_used_at | TIMESTAMP | 最后使用时间 |
| access_count | INT | 访问次数 |


#### memory_nodes 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | TEXT | 用户ID |
| name | TEXT | 节点名称 |
| type | TEXT | 节点类型 (entity)(作保留) |
| properties | JSONB | 属性JSON |
| memory_items | JSON | 关联记忆列表 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### memory_edges 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | TEXT | 用户ID |
| source_node_id | UUID | 源节点ID |
| target_node_id | UUID | 目标节点ID |
| relation_type | TEXT | 关系类型 |
| is_active | BOOLEAN | 是否活跃 |
| created_at | TIMESTAMP | 创建时间 |
| properties | JSONB | 属性JSON |

#### chat_history 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID | 会话ID |
| user_id | TEXT | 用户ID |
| role | TEXT | 角色 (user/assistant) |
| content | TEXT | 消息内容 |
| created_at | TIMESTAMP | 创建时间 |

#### 其他表
此外还有user_info用户表，字段较为简单
config_schema,system_config,user_config配置表，不是重点

### 建表 SQL
导入postgresql.sql即可

## 架构说明

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                     │
│            路由、参数验证、响应格式化                   │
├─────────────────────────────────────────────────────────────┤
│              Orchestrator Layer                       │
│            业务编排、跨模块协调                     │
├─────────────────────────────────────────────────────────────┤
│                Service Layer                         │
│        业务逻辑、会话管理、记忆服务                 │
├─────────────────────────────────────────────────────────────┤
│              Repository Layer                          │
│         数据访问、SQL 封装、数据库交互              │
├─────────────────────────────────────────────────────────────┤
│               Database Layer                       │
│           PostgreSQL、Redis                      │
└─────────────────────────────────────────────────────────────┘
```

### 核心流程图

#### 一次完整的对话流程

```
用户输入
    ↓
获取/创建会话
    ↓
分析用户情绪
    ↓
检索相关记忆 (向量检索 + 图检索)
    ↓
构建提示词 (人设 + 情绪 + 记忆 + 历史)
    ↓
调用 LLM 获取回复
    ↓
保存聊天记录
    ↓
更新会话状态
    ↓
返回回复给用户
    ↓
(后台) 检查会话状态，适时提取记忆
```

#### 记忆提取流程

```
会话超时/结束
    ↓
获取会话的聊天历史
    ↓
调用 LLM 提取记忆
    ↓
向量化记忆内容
    ↓
保存记忆到数据库
    ↓
提取实体，构建知识图谱节点
    ↓
建立实体间关联
    ↓
更新会话状态为 ENDED
```

## 核心模块

### 1. 会话管理 (SessionService)

**文件**：`services/session_service.py`

**功能**：
- 获取或创建用户会话
- 管理会话生命周期
- 会话超时检测
- 记忆提取触发

**状态机**：
```
IDLE → STARTING → CHATTING → MEMORY_EXTRACTING → ENDED
```

**关键方法**：
- `get_session(user_id, device_id)`: 获取或创建会话
- `update(user_id)`: 更新会话活跃时间
- `force_extract_memory(user_id)`: 强制提取记忆并结束会话
- `extract_memory_for_expired_sessions()`: 批量提取超时会话的记忆

### 2. 记忆服务 (MemoryService)

**文件**：`services/memory_service.py`

**功能**：
- 记忆检索（混合检索）
- 记忆提取
- 记忆管理

**混合检索策略**：
1. **向量检索**：使用 Sentence-Transformers 计算语义相似度
2. **图检索**：使用实体匹配器找到相关实体，通过知识图谱检索
3. **合并去重**：合并两个来源的记忆，去除重复
4. **重排序**：根据相关性、重要性、时效性综合排序

**评分公式**：
```
score = 0.45 * similarity + 0.30 * importance + 0.25 * recency
```

**实体匹配**：
- 基于 Aho-Corasick 自动机算法
- 从知识图谱加载所有实体
- 在用户输入中快速匹配实体

**关键方法**：
- `get_memory(user_id, current_text, top_k)`: 检索相关记忆
- `extract_memory(user_id, history)`: 从历史记录提取记忆

### 3. 实体匹配器 (AcEntityMatcher)

**文件**：`utils/entity_matcher.py`

**功能**：
- 高效的实体匹配
- 支持自定义节点添加
- 支持保存和加载自动机

**使用示例**：
```python
matcher = AcEntityMatcher()
matcher.add_node("node-1", "用户")
matcher.add_node("node-2", "小红")
matcher.build()

matches = matcher.match_unique("我想和小红去吃火锅")
# 返回: [("node-2", "小红")]
```

### 4. 对话编排器 (ChatOrchestrator)

**文件**：`orchestrator/chat_orchestator.py`

**功能**：
- 协调各模块完成对话流程
- 调用情感分析、记忆检索、LLM 等
- 返回最终回复

## 设计理念

### 1. 记忆系统设计

基于三个核心维度：

| 维度 | 说明 | 计算方式 |
|------|------|----------|
| **相关性** | 与当前对话的语义相似度 | 向量余弦相似度 |
| **重要性** | 记忆对用户的重要程度 | LLM 评分 (0-1) |
| **时效性** | 记忆的新旧程度 | exp(-delta_days / 7) |

### 2. 知识图谱设计

- **记忆挂载**：记忆挂载在节点上，而非边上
- **实体提取**：自动从对话中提取实体，构建图谱

### 3. 会话生命周期

- **超时机制**：30分钟无活动视为超时
- **记忆提取**：会话结束时自动提取记忆
- **状态保持**：未结束的会话不会被替换

### 4. 外部定时任务

还在设计当中


### 5. 设计灵感

本项目的设计融合了以下产品的理念：

- **XiaoIce (小冰)**：共情计算、场景判断、主动对话策略
- **Replika**：记忆分类、记忆管理
- **Generative AI**：记忆遗忘机制、重要性/时效性/相关性评分
- **MaiBot**：记忆图谱机制，历史记录机制，agent架构

## 开发指南

### 代码规范

- 遵循 PEP 8 编码规范
- 使用类型注解 (Type Hints)
- 模块级文档字符串
- 合理的异常处理

### 添加新的 API

1. 在 `api/` 目录下创建或修改路由文件
2. 定义路由函数，使用 `@router.get`/`@router.post` 装饰器
3. 调用对应的 Service 方法
4. 统一返回格式

### 添加新的 Service

1. 在 `services/` 目录下创建服务文件
2. 定义服务类，包含业务逻辑
3. 在 `main.py` 中注册服务

### 添加新的 Repository

1. 在 `repositories/` 目录下创建数据访问文件
2. 定义 Repository 类，封装 SQL 操作
3. 在 `main.py` 中注册 Repository

## 常见问题

### 1. 向量检索返回结果为空

检查：
- 记忆是否成功向量化
- 向量维度是否为 384
- 查询文本是否与记忆内容相关

### 2. 记忆提取失败

检查：
- LLM API Key 是否正确配置
- 提示词模板是否正确
- 聊天历史是否足够长

### 3. 会话自动结束

原因：
- 会话超时（默认30分钟）
- 记忆提取完成后自动结束

### 4. 数据库连接失败

检查：
- PostgreSQL 服务是否启动
- DATABASE_URL 是否正确
- pgvector 扩展是否安装

## 维护建议
- 增加与硬件对接的部分 如加上处理ws连接的部分，语音转文字调大模型接口文字转语音。
- 调优提示词
- 升级记忆系统


