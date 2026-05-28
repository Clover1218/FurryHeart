# 语音链路对接文档 — Phase 1 ~ Phase 3

---

## 整体架构与分工原则

```
┌──────────────────────────────────────────────────────────┐
│                      API 层                               │
│  ws_api.py ─── WebSocket 入口（why）                       │
│  device_api.py ─── 设备 REST API（clover）                  │
│  auth_api.py / user_api.py / chat_api.py（已有，不涉及）    │
├──────────────────────────────────────────────────────────┤
│                     服务层                                 │
│  ws_service.py ─── WebSocket 事件分发（why+clover）         │
│  ├─ _process_audio_message() 语音事件（why）               │
│  ├─ _process_bind_message()   绑定事件（clover）            │
│  └─ _process_unbind_message() 解绑事件（clover）           │
│                                                           │
│  asr_service.py ─── ASR 语音识别（不动）                    │
│  tts_service.py ─── TTS 语音合成（不动）                    │
│                                                           │
│  llm/deepseek_client.py ─── LLM 客户端（why）              │
│  llm_service.py ─── LLM 服务封装（why）                    │
│                                                           │
│  chat_orchestator.py ─── 对话编排器（why）                  │
│  scene_loader.py ─── 场景文件加载器（Phase 2，clover）      │
│                                                           │
│  embedding_service.py ─── 向量嵌入（Phase 3，clover）       │
│  memory_service.py ─── 记忆服务（Phase 3，why+clover）      │
│  env_service.py ─── 环境信息（Phase 3，clover）             │
│                                                           │
│  device_service.py ─── 设备管理（clover）                   │
│  auth_service.py ─── 认证（clover，已有不动）              │
├──────────────────────────────────────────────────────────┤
│                     数据层                                 │
│  device_repo.py ─── 设备数据库（clover）                   │
│  auth_repo.py ─── 认证数据库（clover，已有不动）           │
│  database/ ─── SQLite 记忆库（Phase 3 新增，clover）        │
└──────────────────────────────────────────────────────────┘
```

**分工原则**：clover = 基础设施层（数据存储/embedding/场景文件），why = 控制流层（编排/LLM/prompt）。两人在不同文件上工作。

---

## Phase 1：跑通基本语音链路

**目标**：ESP32 说话 → ASR → LLM 流式 → TTS → ESP32 播放出声

### 数据流

```
ESP32 发音频 bytes → ws_service._handle_audio() 缓存
  → ESP32 发 {"event": "recording_ended"}
  → _process_audio_message()
    → asr_service.transcribe(pcm)
    → chat_orchestrator.chat_stream(text)   → LLM token 流
    → tts_service.return_audio_generator()  → TTS 音频流
    → send_bytes(chunk)                     → 逐块发回 ESP32
    → send_text({"event": "audio_stream_end"})
    → (可选) send_text({"event": "goodbye"})
```

### 分工

| 文件 | 负责人 | 改动内容 |
|------|--------|---------|
| `services/llm/deepseek_client.py` | why | 新增 `AsyncOpenAI`；新增 `stream_chat(messages)` |
| `services/llm_service.py` | why | 实现 `generate_stream(messages)` |
| `orchestrator/chat_orchestator.py` | why | 实现 `chat_stream(device_id, user_input)` |
| `services/ws_service.py` | why | `_process_audio_message()` await + ping→audio_stream_end |
| `services/ws_service.py` | clover | `_process_bind_message` / `_process_unbind_message` |
| `services/device_service.py` | clover | 设备绑定/解绑/注册（已有逻辑） |

---

## Phase 2：Tool 系统

**前置条件**：Phase 1 完成。

### 2.1 [END] 对话结束标记

**原理**：system prompt 中指引 LLM 在告别时末尾加 `[END]`。TTS 层的 `return_audio_generator()` 已有检测逻辑——消费 token 时若检测到 `[END]` 则剥离标记、停止合成、设 `goodbye[0]=True`。ws_service 拿到 goodbye 后发信号给 ESP32。

| 文件 | 负责人 | 改动 |
|------|--------|------|
| `core/prompt.py` | why | system prompt 追加 [END] 指引段 |

### 2.2 select_scene 场景工具

**原理**：第一轮 LLM 调用带 tools=[select_scene]。若 LLM 调用 `select_scene("work/pressure")`，加载场景提示词做第二轮不带 tools 的回复。否则直接输出。

**SceneLoader 接口约定**：

```python
class SceneLoader:
    def get_scene_content(self, scene_id: str) -> str | None
    def get_base_prompt(self) -> str
    def get_all_scene_ids(self) -> list[str]
```

场景文件位置 `提示词/`：

```
提示词/
├── base.txt                     # 基础人格设定
├── classifier.txt               # 场景分类器
├── daily.txt                    # 日常闲聊
├── work/   {pressure, conflict, career}.txt
├── emotion/{loneliness, relationship, anxiety}.txt
└── family/ {origin, expectations}.txt
```

| 文件 | 负责人 | 改动 |
|------|--------|------|
| 新增 `services/scene_loader.py` | **clover** | 场景文件加载器（读文件+缓存） |
| `提示词/*.txt` | **clover** | 9 个场景文件内容优化 |
| `deepseek_client.py` | **why** | 新增 `stream_chat_with_tools(messages, tools)` |
| `llm_service.py` | **why** | 新增 `generate_stream_with_tools()` |
| `chat_orchestator.py` | **why** | 重写 `chat_stream()`：tool calling 编排 |
| `core/prompt.py` | **why** | 追加场景工具使用指引 |

**参考代码**：`speech_commands/server/modules/prompt_loader.py`、`speech_commands/server/modules/llm.py`、`speech_commands/server/core/orchestrator.py`

---

## Phase 3：记忆系统

**前置条件**：Phase 2 完成。

### 架构

```
通道一：记忆注入（会话开始时）
  SQLite 读取（档案+近10条会话+待发生事件+环境）→ 拼入 system prompt
  覆盖 ~90% 需求：情感连续性、主动关怀

通道二：向量检索（按需触发）
  LLM 调用 search_memory(query) → embedding → 余弦 top-3
  覆盖 ~10% 需求：用户明确追溯旧事
```

### 存储层（clover）

`backend/database/` 下建三个文件：

#### `schema.py`

```sql
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id       TEXT UNIQUE NOT NULL,
    profile_json    TEXT DEFAULT '{}',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL,
    date        TEXT NOT NULL,               -- "2026-05-06"
    emotion     TEXT,
    events      TEXT NOT NULL,               -- JSON array
    embedding   BLOB,                        -- float32×768 = 3072 bytes
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE upcoming_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL,
    content     TEXT NOT NULL,
    est_date    TEXT NOT NULL,
    precision   TEXT DEFAULT 'day',           -- "day" / "month"
    source_date TEXT NOT NULL,
    status      TEXT DEFAULT 'pending',       -- pending / passed / expired
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_device ON sessions(device_id);
CREATE INDEX idx_upcoming_device ON upcoming_events(device_id);
CREATE INDEX idx_upcoming_status ON upcoming_events(device_id, status);
```

#### `connection.py` — aiosqlite 连接管理，提供 `get_db()`

#### `repositories/` — 三个 repo：

| Repo | 方法 |
|------|------|
| `user_repo.py` | `get_profile(device_id)`, `update_profile(device_id, profile_json)` |
| `session_repo.py` | `add_session(...)`, `get_recent(device_id, limit=10)`, `get_all_excluding_recent(device_id, skip_recent=10)` |
| `event_repo.py` | `get_by_status(device_id, status)`, `add_event(...)`, `update_status(event_id, status)` |

#### embedding 列编码

存 BLOB（float32 二进制），不存 JSON TEXT：

```python
import struct
def vec_to_blob(vec: list[float]) -> bytes:
    return struct.pack(f'{len(vec)}f', *vec)         # 768×4 = 3072 bytes

def blob_to_vec(blob: bytes) -> list[float]:
    return list(struct.unpack(f'{len(blob)//4}f', blob))
```

### EmbeddingService（clover）

新建 `services/embedding_service.py`：

```python
class EmbeddingService:
    async def embed_text(self, text: str) -> list[float] | None
    def cosine_similarity(self, a: list[float], b: list[float]) -> float
    async def search_similar_sessions(self, device_id: str, query: str,
        top_k: int = 3, threshold: float = 0.5, skip_recent: int = 10) -> list[dict]
```

| 参数 | 值 |
|------|-----|
| API | DashScope text-embedding-v3，dimension=768 |
| 重试 | 失败重试 2 次 + 指数退避，耗尽返回 None |
| top_k | 3 |
| threshold | 0.5 |

### EnvironmentService（clover）

新建 `services/env_service.py`：

```python
class EnvironmentService:
    def get_date_str(self) -> str         # "今天是2026年5月28日，星期四"
    async def get_weather(self, city: str | None) -> str  # "晴，26°C"
```

- 城市来源：profile.city 优先 → IP 定位兜底
- 天气：和风天气免费 API

### MemoryService（按方法分）

| 方法 | 负责人 | 说明 |
|------|--------|------|
| `get_memory_injection(device_id) → str` | **clover** | 读 DB 组装注入文本 |
| `search_memory(device_id, query) → str` | **clover** | 调 EmbeddingService 检索 |
| `extract_memory(device_id, session_text)` | **why** | LLM 提取日记 → 写 sessions + embedding |
| `update_profile(device_id, session_text)` | **why** | LLM 更新用户档案 |
| `cleanup_expired_events(device_id)` | **why** | 日期状态流转 |

### system prompt 最终结构

```
{env_service.get_date_str()}。{城市}，{天气}。    ← clover: env

《历史记忆》                                       ← clover: memory_injection
【用户档案】...
【最近的对话记录】...
【即将发生的事】...
【刚过去的事】...

{base.txt 人格设定}                               ← why: prompt 拼接
## 场景工具
## 记忆搜索
## 结束对话
```

---

## 冲突规避

### 多人共改的文件

`ws_service.py` 按方法隔离：

| 方法 | 谁动 |
|------|------|
| `_process_audio_message()` / `_handle_audio()` | **why** |
| `_process_bind_message()` / `_process_unbind_message()` | **clover** |
| `handle_connection()` | 尽量不动，动了通知对方 |

`memory_service.py` 按方法隔离（见上表）。

**规范**：改代码前先 `git pull --rebase`，查一下对方最近提交 `git log --oneline -5 <file>`。必须同时改同一文件时，一个人先改完提交，另一人 rebase 后再改。

---

## 测试

```bash
cd backend
# .env 需配置 DEEPSEEK_API_KEY + DASHSCOPE_API_KEY
python main.py
```

设备注册（否则 ws_api.py 拒绝连接）：

```sql
INSERT INTO device_info (device_id, status) VALUES ('test_device_001', 'active');
```
