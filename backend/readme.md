# HeartBot Backend
此为心偶项目的后端，采用Python开发。选用FastAPI作为基础，命名规范遵循PEP 8。
具体配置可在.env里调整
目前已实现简单的记忆存储与提取功能,用SentenceTransformer("all-MiniLM-L6-v2")作向量化。
用户系统正在开发。
## 目前想法

基于小冰(XIAOICE)的设计，引入“共情计算模块”，每回合用大模型来动态判断当前用户场景和情绪，比如低能量，想玩游戏，想听歌，调用不同的提示词和不同的回复情感进行回复。并在合适的时候采用主动说话策略，如话题沉重，用户不想聊天，可以主动出击换话题，或者从库中拉出未提及的记忆进行聊天。同时小冰的A/B测试数据为我们抛出了另一个问题：短期记忆与长期关系的平衡。如任务型技能（如查天气）会降低CPS（每轮对话数），但能建立信任；情感型技能（如闲聊）能拉高CPS，因此，情感型记忆似乎该赋予更高重要性。
基于Replika的设计，将获得的记忆分为Background,Favorites,Appearance,Hopes&Goals,Opinions,Personality,Other。这样分的好处在于全面。同时Replika可以主动添加Family&Friend(Pets)，具体有待研究(才刚下过来体验两天)。
基于Generative AI的设计，模拟人的记忆遗忘机制，在给大模型选取参考记忆的时候引入“重要性”“时效性”“相关性”，即记忆对用户的重要性，产生记忆的时间离现在的时间跨度，向量相似度。三者以不同比例作为选取参考。同时隔一段时间选取最近记忆生成焦点问题，依赖焦点问题和最近记忆生成高层认知insight，放入记忆中。

如此看来，记忆的结构表应该如下定义：
CREATE TABLE memories (
  id UUID PRIMARY KEY,
  user_id TEXT,
  device_id TEXT,
  content TEXT,                     -- 一句话记忆，便于向量检索
  type TEXT,                        -- event / insight (为高层认知准备)
  source_memory_ids JSONB,          -- 仅 insight 使用 (为高层认知准备)
  tags JSONB                        -- 事件标签 (模仿Replika,但不强分类,给事件打标签)
  embedding VECTOR,                 -- 向量 
  emotion TEXT,                     -- 记忆的情感
  emotion_intensity FLOAT,          -- 情感强度
  importance FLOAT,                 -- 重要性 (在0任务型和1情感型之间打分)
  created_at TIMESTAMP,             -- 创建时间 (为"时效性"提供计算依据)
  used_count INT DEFAULT 0,         -- 被使用次数 (为"时效性"提供计算依据)
  last_used_at TIMESTAMP,           -- 上次使用时间 (为"时效性"提供计算依据)
);
以下是用户画像的定义:
CREATE TABLE user_profiles (
  user_id TEXT PRIMARY KEY,
  traits JSONB,          -- 稳定人格
  preferences JSONB,     -- 偏好(情感人格方面的)
  relationships JSONB,   -- 人际关系
  current_state JSONB,   -- 当前用户情绪状态
  updated_at TIMESTAMP
);
整个系统分为三个模块：
记忆系统、情感计算、用户画像

一次完整的交互流程如下：

用户说话->通过情感计算层获取当前可能的场景与用户情绪->根据场景与情绪与用户说的话通过记忆系统选取记忆->把用户画像、场景和情绪相关提示词(AI人设和回复策略)、相关记忆、历史对话注入Prompt，获取恢复->视情况提取新记忆、更新用户画像、生成高层认知。

一些细节：
1.画像改变应不宜过多，可记忆存到一定程度后，或者生成一定insight后进行更新
2.记忆选取使用混合检索：关键词(标签)检索+向量检索。并根据相关性、时效性、重要性排名选Top-k个

## 用户设置

prompt.system_base_prompt
系统基础人设
prompt.memory_extract_prompt

## 结构
![结构图](./flowchart.svg)
```
backend/
├── api/   
│   ├── auth_api.py # 认证相关api
│   └── chat_api.py # 对话相关api
├── core/
│   ├── config.py # 配置
│   ├── db.py # 数据库导入
│   ├── exceptions.py 
│   ├── logger.py # 日志
│   └── prompt.py # 提示词配置文件
├── logs/
├── models/
│   └── auth_model.py
├── orchestrator/
│   ├── __init__.py
│   └── chat_orchestator.py # 对话业务编排
├── repositories/
│   ├── __init__.py
│   ├── memory_repo.py # 记忆相关数据操作
│   └── user_repo.py # 用户相关数据操作
├── schemas/
├── services/
│   ├── llm/
│   │   └── iflow_client.py
│   ├── __init__.py
│   ├── auth_service.py # 认证服务
│   ├── embedding_service.py # 向量化服务 
│   ├── emotion_service.py # 情感检测服务
│   ├── history_service.py # 历史记录管理服务
│   ├── llm_service.py # LLM服务
│   ├── memory_service.py # 记忆服务
│   ├── session_service.py # 会话管理服务
│   └── user_service.py # 用户相关服务
├── main.py # 组装service与repo,启动FastAPI
├── readme.md 
```
## 接口
### /api/auth/wx_login
#### 接口说明
通过微信登录凭证(code)换取用户登录认证令牌(token)与用户唯一标识ID(user_id)
#### 请求路由
```
POST /api/auth/wx_login 
```
#### 请求参数
| 参数名 | 类型 | 必填 | 说明|
|------|------|----------|---|
|code|string|是|微信登录凭证|

#### 请求示例
```
{
   "code":"wx1165156"
}
```
#### 响应参数
| 参数名 | 类型 |说明|
|------|------|---------|
|code|int|状态码|
|message|string|返回信息|
|data|object|返回数据|
|token|string|用户token|
|is_new_user|boolean|是否新用户
|user_id|string|用户唯一标识|

#### 响应示例
```
{
   "code":0,
   "message":"success",
   "data":{
      "token":"afaea2-faf32ga-adwd",
      "is_new_user":true,
      "user_id":"4949116489"
   }
}
```
#### 附加说明
拿取到的token需存在Authorization首部，格式：`Authorization: Bearer <token>`
### /api/chat/create
#### 接口说明
用于获取会话id，需带上token
#### 请求路由
```
GET /api/chat/create
```
#### 请求参数
无
#### 请求示例
无
#### 响应参数
| 参数名 | 类型 |说明|
|------|------|---------|
|session_id|string|会话id|

#### 响应示例
```
{
   "code":0,
   "message":"success",
   "data":{
      "session_id":"po03i2-wfwg3w-3t32g",
   }
}
```
### /api/chat
#### 接口说明
通过此接口与云端进行文字版对话,请求需带上token
#### 请求路由
```
POST /api/chat/
```
#### 请求参数
| 参数名 | 类型 | 必填 | 说明|
|------|------|----------|---|
|question|string|是|用户输入|
|session_id|string|是|会话id|
#### 请求示例
```
{
   "question":"你是谁",
   "session_id":"po03i2-wfwg3w-3t32g"
}
```
#### 响应参数
| 参数名 | 类型 |说明|
|------|------|---------|
|answer|string|模型回复|

#### 响应示例
```
{
   "code":0,
   "message":"success",
   "data":{
      "answer":"我是HeartBot",
   }
}
```
## 数据库建表函数
PostgreSQL
```
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY,

    user_id TEXT NOT NULL,
    chat_time TIMESTAMP NOT NULL,

    -- 核心内容
    content TEXT,
    summary TEXT,
    event_sentence TEXT,
    feeling TEXT,

    -- 时间地点
    location TEXT,
    event_time DATE,

    -- 情绪
    emotion TEXT,
    emotion_intensity FLOAT DEFAULT 0.5,

    -- 分类
    memory_type TEXT,
    scene_type TEXT,
    tags TEXT[],

    -- 向量
    embedding VECTOR(384),

    -- 记忆机制
    importance_score FLOAT DEFAULT 0.5,
    access_count INT DEFAULT 0,
    last_accessed_at TIMESTAMP,

    is_pinned BOOLEAN DEFAULT FALSE,

    raw_json JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,

    role TEXT NOT NULL,         -- user / assistant
    content TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_mem_time ON memories(chat_time);
CREATE INDEX IF NOT EXISTS idx_mem_tags ON memories USING GIN(tags);
```