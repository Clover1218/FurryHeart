# 绒绒心语-前后端测试
此文档面向硬件、前端、后端、提示词负责人，方便快速掌握项目结构并实现并行开发
## 当前代办
### TOP1 完成硬件端的绑定闭环
#### 写在前面：
目前方案：
服务器ws连接地址为ws://1.13.15.207:8000/{device_id}
device_id出厂时分配，唯一，写死在硬件里
#### 主要绑定流程：
- (硬件配网成功后)小程序端向云端发起绑定请求 ↓
- 云端返回一个绑定token给小程序端 ↓
- 小程序端将token通过蓝牙写入硬件端 ↓
- 硬件端**通过ws连接**将token发给云端进行验证 ↓
- 云端返回验证结果，硬件**通过ws连接**接收，同时给云端再发一个确认的信息，若失败，硬件回到初始状态；若成功，do what you want ↓

#### 建议交互格式：
##### 硬件发token给云端:
```json
{
    "event": "device_send_bind_token",
    "data": {
        "token": "a1b2c3...",
    }
}
```
##### 硬件接收云端的验证结果：
说明:
success的值为true或者false。
当success为false时，不带user_id。
当success为true时，带user_id，硬件端建议存储user_id。
```json
{
    "event": "device_bind_confirmed",
    "data": {
        "success": true,
        "user_id": "xxx" 
    }
}
```


### TOP2


## 当前项目状态

由于需要先测试记忆系统和提示词，准备Web端测试成熟后，再适配硬件端，最后移植到小程序端。后端已经预留适配两端的接口。

- **后端（/backend）**：FastAPI后端，具备基础的用户系统、会话管理、对话历史存储、记忆存储与检索、大模型对话、设置功能。
- **前端（/heartbot-frontend）**：Vue 3 + Vite（TypeScript）前端。与后端适配，具备基础用户登录功能、对话功能、增量式历史对话记录拉取、记忆图谱展示。

详细接口文档放在各文件夹中
## 技术栈

### 后端

| 层级               | 技术栈                                           |
| ------------------ | ------------------------------------------------ |
| 语言               | Python 3.12.10                                   |
| Web服务器框架      | FastAPI                                          |
| 主数据库           | PostgreSQL                                       |
| 缓存/会话          | Redis                                            |
| LLM                | DeepSeek，由LLMService封装                       |
| 向量数据库         | pgvector扩展                                     |
| 图数据库           | PostgreSQL（节点表加边表模拟）                   |

### 前端

| 层级       | 技术栈                     |
| ---------- | -------------------------- |
| 框架       | Vue3                       |
| 构建       | Vite                       |
| 状态管理   | Pinia                      |
| 路由       | Vue-Router                 |
| UI库       | NaiveUI                    |
| 图展示     | AntG6                      |

## 项目部署
### 前期准备
需要安装：
- PostgreSQL（需安装pgvector扩展）
- Redis
- Python 3.12.10+ 环境
- Node.js v22.18.0+ 环境

然后用`backend/db/postgres.sql`文件导入表结构。

打开项目文件夹，进入`backend`，填写环境变量文件`.env`，以下是必须修改的重要变量：

| 变量           | 说明                 |
| -------------- | -------------------- |
| DB_HOST        | PostgreSQL主机名     |
| DB_PORT        | PostgreSQL端口       |
| DB_USER        | PostgreSQL用户名     |
| DB_PASSWORD    | PostgreSQL用户对应密码 |
| DB_NAME        | PostgreSQL对应数据库名 |
| REDIS_HOST     | Redis主机名          |
| REDIS_PORT     | Redis端口            |
| REDIS_PASSWORD | Redis密码            |

杂项：

| 变量         | 说明         |
| ------------ | ------------ |
| SERVER_HOST  | 后端主机名   |
| SERVER_PORT  | 后端端口     |

### 项目运行

**后端：**
注：第一次运行时必须有pip install -r requirements.txt，后续运行可不带
```powershell
cd backend
pip install -r requirements.txt
python main.py
```

**前端：**
注：第一次运行时必须有npm install，后续运行可不带
```powershell
cd heartbot-frontend
npm install 
npm run dev
```