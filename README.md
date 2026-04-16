# Fitness Agent - 智能健身助手

基于大语言模型的智能健身助手 API，提供专业的健身咨询、训练计划生成、身体指标计算等功能。

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [API 文档](#api-文档)
- [核心模块](#核心模块)
- [部署指南](#部署指南)
- [开发指南](#开发指南)

---

## 功能特性

### AI 对话
- 智能意图识别（健身咨询、训练计划、身体指标、营养建议等）
- 多轮对话支持，上下文记忆
- 流式响应（SSE）

### 身体指标计算
- BMI 计算与健康评估
- BMR（基础代谢率）计算
- 体脂率估算

### 训练计划生成
- 根据目标（减脂/增肌/塑形）生成个性化计划
- 支持不同训练水平（初级/中级/高级）
- 包含动作指导和训练安排

### 知识库检索（RAG）
- 语义搜索健身知识
- ChromaDB 向量存储
- Qwen Embedding 嵌入

### 用户系统
- JWT 认证
- 用户画像管理
- 训练记录持久化

### 可观测性
- Prometheus 指标监控
- 结构化日志
- 链路追踪

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| Agent 框架 | LangChain + LangGraph |
| LLM | 通义千问 (Qwen) |
| 向量数据库 | ChromaDB |
| 缓存 | Redis |
| 数据库 | PostgreSQL |
| 监控 | Prometheus + Grafana |
| 容器化 | Docker + Docker Compose |

---

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd fitness-agent

# 2. 创建环境变量文件
cp .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 访问 API 文档
open http://localhost:8000/docs
```

### 方式二：本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -e .

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 启动 Redis 和 PostgreSQL
# 确保 Redis 运行在 localhost:6379
# 确保 PostgreSQL 运行在 localhost:5432

# 5. 初始化数据库
createdb fitness_agent

# 6. 启动服务
uvicorn app.main:app --reload
```

### 健康检查

```bash
curl http://localhost:8000/health
```

返回示例：
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "redis": "ok"
}
```

---

## 环境配置

### 必需配置

创建 `.env` 文件：

```env
# 通义千问 API Key（必需）
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 数据库连接（必需）
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/fitness_agent

# Redis 连接（必需）
REDIS_URL=redis://localhost:6379/0

# JWT 密钥（生产环境必须修改）
JWT_SECRET_KEY=your_secure_secret_key
```

### 完整配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | fitness-agent |
| `APP_ENV` | 运行环境 | development |
| `APP_DEBUG` | 调试模式 | false |
| `DASHSCOPE_API_KEY` | 通义千问 API Key | - |
| `LLM_MODEL_NAME` | LLM 模型 | qwen-max |
| `LLM_TEMPERATURE` | 生成温度 | 0.7 |
| `LLM_MAX_TOKENS` | 最大 Token 数 | 2000 |
| `DATABASE_URL` | 数据库连接 | - |
| `REDIS_URL` | Redis 连接 | - |
| `JWT_SECRET_KEY` | JWT 密钥 | - |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间 | 120 |
| `RATE_LIMIT_REQUESTS` | 限流请求数 | 60 |
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_FORMAT` | 日志格式 | json |

---

## API 文档

### 基础 URL

```
http://localhost:8000
```

### 在线文档

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API 端点

#### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | API 基本信息 |
| GET | `/health` | 健康检查 |
| GET | `/metrics` | Prometheus 指标 |

#### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 用户注册 |
| POST | `/auth/login` | 用户登录 |
| GET | `/auth/me` | 获取当前用户 |
| PATCH | `/auth/me` | 更新用户画像 |
| GET | `/auth/verify` | 验证 Token |

#### 对话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat/` | 发送消息 |
| GET | `/chat/stream` | 流式对话 |
| POST | `/chat/stream` | 流式对话 (POST) |
| GET | `/chat/history/{session_id}` | 获取历史消息 |
| DELETE | `/chat/history/{session_id}` | 清空历史 |
| DELETE | `/chat/sessions/{session_id}` | 删除会话 |

#### 工具接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tools/` | 工具列表 |
| GET | `/tools/{tool_name}` | 工具详情 |
| GET | `/tools/openai/format` | OpenAI 格式定义 |

### 使用示例

#### 用户注册

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

#### 用户登录

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

返回：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### 发送消息

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "帮我制定一个减脂计划"
  }'
```

返回：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "response": "好的，我来为您制定一个减脂计划...",
    "session_id": "sess_abc123",
    "trace_id": "trace_xyz"
  }
}
```

#### 流式对话

```bash
curl -N http://localhost:8000/chat/stream?query=你好
```

返回（SSE 格式）：
```
event: start
data: {"session_id": "sess_xxx", "trace_id": "trace_xxx"}

event: token
data: {"content": "你好"}

event: token
data: {"content": "你好！有什么可以帮助你的？"}

event: done
data: {"session_id": "sess_xxx", "response_length": 36}
```

#### 计算身体指标

```python
import httpx

# 计算 BMI
response = httpx.post(
    "http://localhost:8000/chat/",
    json={"query": "我身高175cm，体重70kg，帮我算一下BMI"}
)
print(response.json())

# 计算体脂率
response = httpx.post(
    "http://localhost:8000/chat/",
    json={"query": "男性，腰围80cm，颈围35cm，身高175cm，算一下体脂率"}
)
print(response.json())
```

---

## 核心模块

### Agent 状态机

```
用户输入
    │
    ▼
┌─────────┐
│ Intent  │ ← 意图识别
└────┬────┘
     │
     ▼
┌─────────┐
│ Router  │ ← 路由决策
└────┬────┘
     │
     ├─→ [knowledge] → Retriever → Generator
     ├─→ [tool]      → ToolExecutor → Generator
     ├─→ [mcp]       → MCPExecutor → Generator
     └─→ [chat]      → Generator
```

### 意图类型

| 意图 | 说明 | 路由 |
|------|------|------|
| `fitness_consult` | 健身咨询 | knowledge |
| `plan_request` | 训练计划请求 | tool |
| `body_metrics` | 身体指标计算 | tool |
| `nutrition_consult` | 营养咨询 | knowledge |
| `exercise_guide` | 动作指导 | knowledge |
| `chitchat` | 闲聊 | chat |

### 工具列表

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `calculate_bmi` | BMI 计算 | weight, height |
| `calculate_bmr` | BMR 计算 | weight, height, age, gender |
| `calculate_body_fat` | 体脂率计算 | waist, neck, height, gender |
| `generate_plan` | 训练计划生成 | goal, level, frequency |
| `get_exercise_info` | 动作详情 | exercise_name |
| `list_exercises` | 动作列表 | category |

### RAG 检索

知识库存储在 `data/knowledge/` 目录，支持 Markdown 格式：

```markdown
---
title: 深蹲动作指南
category: strength
tags: [腿部, 核心]
---

# 深蹲

深蹲是最有效的下肢训练动作之一...
```

---

## 部署指南

### Docker 部署

```bash
# 构建镜像
docker build -t fitness-agent:latest .

# 运行容器
docker run -d \
  --name fitness-agent \
  -p 8000:8000 \
  -e DASHSCOPE_API_KEY=your_key \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e REDIS_URL=redis://... \
  fitness-agent:latest
```

### Docker Compose 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 启用监控

```bash
# 启动包含监控的完整服务
docker-compose --profile monitoring up -d

# 访问 Prometheus
open http://localhost:9090

# 访问 Grafana
open http://localhost:3000  # admin/admin
```

### 生产环境检查清单

- [ ] 修改 `JWT_SECRET_KEY`
- [ ] 设置 `APP_ENV=production`
- [ ] 设置 `APP_DEBUG=false`
- [ ] 配置 HTTPS
- [ ] 配置 CORS 白名单
- [ ] 配置数据库备份
- [ ] 配置日志收集

---

## 开发指南

### 项目结构

```
fitness-agent/
├── app/
│   ├── api/              # API 路由和依赖
│   │   ├── deps.py       # 依赖注入
│   │   ├── response.py   # 统一响应格式
│   │   ├── routes/       # 路由定义
│   │   └── schemas/      # 请求/响应模型
│   ├── agent/            # Agent 核心
│   │   ├── graph.py      # 状态机图
│   │   ├── state.py      # 状态定义
│   │   ├── nodes/        # 处理节点
│   │   └── memory/       # 会话管理
│   ├── auth/             # 认证模块
│   ├── config/           # 配置管理
│   ├── db/               # 数据库模型
│   ├── llm/              # LLM 封装
│   ├── mcp/              # MCP 服务
│   ├── rag/              # RAG 检索
│   ├── tools/            # 工具定义
│   ├── utils/            # 工具函数
│   └── main.py           # 应用入口
├── data/
│   ├── knowledge/        # 知识库文档
│   └── chroma/           # 向量存储
├── tests/                # 测试用例
├── docs/                 # 文档
├── deploy/               # 部署配置
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并查看覆盖率
pytest tests/ --cov=app --cov-report=html

# 运行特定测试
pytest tests/test_tools.py -v
```

### 代码风格

```bash
# 格式化代码
black app/

# 代码检查
ruff check app/

# 类型检查
mypy app/
```

### 添加新工具

1. 在 `app/tools/` 创建工具文件：

```python
# app/tools/my_tool.py
from app.tools.base import BaseTool, ToolResult, ToolParameterSchema

class MyTool(BaseTool):
    name = "my_tool"
    description = "工具描述"
    parameters = [
        ToolParameterSchema(
            name="param1",
            type="string",
            description="参数描述",
            required=True,
        ),
    ]

    async def execute(self, **kwargs) -> ToolResult:
        result = do_something(kwargs["param1"])
        return ToolResult.success(result)
```

2. 注册工具：

```python
# app/tools/__init__.py
from app.tools.my_tool import MyTool

def register_my_tools():
    from app.tools.registry import get_tool_registry
    registry = get_tool_registry()
    registry.register(MyTool())
```

### 添加新知识

1. 在 `data/knowledge/` 创建 Markdown 文件：

```markdown
---
title: 知识标题
category: category_name
---

# 知识内容

详细内容...
```

2. 重新索引：

```python
from app.rag.loader import KnowledgeLoader
from app.rag.indexer import get_indexer

loader = KnowledgeLoader("./data/knowledge")
documents = loader.load_all()

indexer = get_indexer()
indexer.add_documents(documents)
```

---

## 监控指标

### Prometheus 指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `chat_requests_total` | Counter | 对话请求总数 |
| `chat_latency_seconds` | Histogram | 对话延迟分布 |
| `llm_tokens_total` | Counter | Token 消耗 |
| `tool_calls_total` | Counter | 工具调用次数 |
| `rag_hits_total` | Counter | RAG 命中次数 |
| `error_total` | Counter | 错误总数 |

---

## 故障排除

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 检查连接
psql -h localhost -U postgres -d fitness_agent
```

#### 2. Redis 连接失败

```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试连接
redis-cli ping
```

#### 3. API Key 无效

确保 `DASHSCOPE_API_KEY` 配置正确，可以在 [阿里云控制台](https://dashscope.console.aliyun.com/) 获取。

#### 4. 流式响应不工作

确保使用 `curl -N` 或支持 SSE 的客户端。

---

## 许可证

MIT License
