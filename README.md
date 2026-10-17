# Couple-Site Agent Service (Python)

为 Couple-Site 提供的 AI Agent 微服务，基于 FastAPI 构建。作为 Java 后端的唯一 AI 调用方，提供 RAG 检索增强、SSE 流式对话、长文本 Map-Reduce 摘要以及向量数据库同步能力。

## ✨ 核心特性

- **RAG 检索增强**：基于 Qdrant 向量库，结合 **MQE (多查询扩展)** 策略，大幅提升口语化提问的召回率。
- **SSE 流式对话**：基于 FastAPI `StreamingResponse`，严格遵循契约返回 `data: {"content":"..."}`，支持前端打字机效果。
- **多轮会话记忆**：基于 SQLite 实现上下文持久化，默认保留最近 10 轮对话，断线自动保存。
- **长文本分治摘要**：针对超长笔记自动触发 Map-Reduce 分治，解决大模型上下文超限问题。
- **幂等向量入库**：基于 UUIDv5 实现确定性 Point ID，保证同业务数据的重复 `upsert` 覆盖与 `delete` 幂等。
- **全链路追踪**：基于 Python `ContextVar` 实现 `trace_id` 跨线程日志注入，方便与 Java 侧日志对齐排查。

## 🛠️ 技术栈

- **Web 框架**：FastAPI + Uvicorn
- **LLM 接入**：OpenAI SDK（直连 DeepSeek）
- **Embedding**：DashScope `text-embedding-v3`（OpenAI 兼容模式）
- **向量数据库**：Qdrant Client
- **本地存储**：SQLite3 (多轮会话历史)
- **配置管理**：pydantic-settings
- **测试工具**：pytest + httpx

## 🚀 快速启动

### 1. 环境准备
确保已安装 Python 3.10+ 和 Qdrant 服务。

```bash
# 启动本地 Qdrant（如果你用的是 Docker）
docker run -d -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage" qdrant/qdrant

# 初始化 Python 虚拟环境
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，并填入必要的 API Key：

```env
# 服务鉴权（与 Java 侧保持一致）
AGENT_KEY=change-me
HOST=127.0.0.1
PORT=8001
LOG_LEVEL=INFO

# LLM (DeepSeek)
LLM_API_KEY=sk-你的deepseek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-flash

# 嵌入模型 (DashScope)
DASHSCOPE_API_KEY=sk-你的dashscope密钥
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBED_MODEL_NAME=text-embedding-v3
EMBED_DIM=1024

# Qdrant (本地或云端)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# 检索策略开关
RETRIEVAL_USE_MQE=true
RETRIEVAL_USE_HYDE=false
```

### 3. 启动服务
```bash
python -m app.main
```
服务默认运行在 `http://127.0.0.1:8001`，API 文档见 `http://127.0.0.1:8001/docs`。

## 📡 接口清单

| 方法 | 路径 | 描述 |
|---|---|---|
| `POST` | `/v1/ingest` | 业务数据同步（幂等 upsert/delete） |
| `POST` | `/v1/chat` | SSE 流式对话（多轮记忆 + 检索增强） |
| `POST` | `/v1/summarize` | 内容摘要（支持长文本分块） |
| `GET` | `/v1/health` | 探活与依赖自检 |

> 所有接口（除 health 外）需携带请求头：`X-Agent-Key: <your-key>`

### 接口调用示例（Chat）

```bash
curl.exe -X POST http://127.0.0.1:8001/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: change-me" \
  -d '{
    "trace_id": "a1b2c3d4e5f60718",
    "user_id": 1,
    "couple_id": 1,
    "session_id": "couple1",
    "message": "我今天干了什么？",
    "scope": "couple",
    "scope_id": 1
  }'
```

## 📂 目录结构

```text
agent-demo/
├── app/
│   ├── api/
│   │   └── routes/          # 路由层（chat / ingest / summarize / health）
│   ├── core/                # 核心逻辑（异常信封、文本切分、命名空间）
│   ├── models/
│   │   ├── orm/             # ORM 模型
│   │   └── schemas/         # Pydantic 请求响应模型
│   ├── prompts/             # Prompt 统一管理
│   ├── services/            # 业务逻辑层（LLM、向量、检索、会话、摘要）
│   ├── utils/               # 工具函数（幂等 upsert）
│   ├── config.py            # 全局配置
│   ├── dependencies.py      # 依赖注入
│   ├── logging_conf.py      # 日志配置（支持 trace_id）
│   ├── test_settings.py     # 测试配置
│   └── main.py              # FastAPI 入口
├── test/                    # 测试脚本（供开发调试）
├── memory_data/             # SQLite 运行时数据（不入库）
├── .env.example             # 环境变量模板
├── requirements.txt
└── README.md
```

## 🧪 开发测试

项目提供了一系列脚本供开发调试使用：

- **测试 Query 检索效果**：`python -m test.test_retrieval`
- **测试灌库（造数据）**：`python -m test.seed_ingest`
- **测试多轮会话**：`python -m test.test_session`
- **测试鉴权与契约（pytest）**：`pytest test/test_ingest.py -v`

## ⚙️ 核心设计说明

1. **向量入库幂等**：通过 `uuid.uuid5(NAMESPACE_DNS, f"{biz_type}:{biz_id}")` 生成确定性 Point ID，保证 Java 重试时覆盖旧数据而不是新增。
2. **检索策略**：`query_processor` 会先清洗掉 `@bot` 前缀，然后根据开关决定是否生成 MQE 扩展查询。多路召回结果会在内存中按 `biz_id` 去重并取最高分，最后截取 `top_k` 送入 Prompt。
3. **SSE 跨线程**：由于 FastAPI 的 `StreamingResponse` 会在线程池中迭代同步生成器，日志模块禁止使用 `bind_trace` (Token reset)，统一使用 `set_trace` 修复 TraceID 丢失问题。
