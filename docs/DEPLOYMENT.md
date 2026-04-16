# 部署指南

## 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (可选)

## 快速开始

### 使用 Docker Compose (推荐)

```bash
# 1. 克隆项目
git clone <repository-url>
cd fitness-agent

# 2. 创建环境变量文件
cp .env.example .env
# 编辑 .env 文件，填写必要的配置

# 3. 启动所有服务
docker-compose up -d

# 4. 检查服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f app
```

### 手动部署

#### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

pip install -e .
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

必需配置:
- `DASHSCOPE_API_KEY`: 通义千问 API Key
- `DATABASE_URL`: PostgreSQL 连接字符串
- `REDIS_URL`: Redis 连接字符串
- `JWT_SECRET_KEY`: JWT 密钥 (生产环境必须修改)

#### 3. 初始化数据库

```bash
# 创建数据库
createdb fitness_agent

# 运行迁移
alembic upgrade head
```

#### 4. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 服务端点

| 端点 | 说明 |
|------|------|
| `/` | API 信息 |
| `/health` | 健康检查 |
| `/docs` | Swagger 文档 |
| `/metrics` | Prometheus 指标 |
| `/chat` | 对话接口 |
| `/chat/stream` | 流式对话 |
| `/tools` | 工具列表 |
| `/auth/login` | 用户登录 |
| `/auth/register` | 用户注册 |

## 监控配置

### Prometheus

1. 启动带监控的完整服务:

```bash
docker-compose --profile monitoring up -d
```

2. 访问 Prometheus: http://localhost:9090
3. 访问 Grafana: http://localhost:3000 (admin/admin)

### 关键指标

- `chat_requests_total`: 对话请求总数
- `chat_latency_seconds`: 对话延迟
- `llm_tokens_total`: Token 消耗
- `tool_calls_total`: 工具调用次数

## 性能优化

### 缓存配置

LLM 响应缓存默认启用，配置:
- 缓存 TTL: 1 小时
- 存储后端: Redis

### 连接池

数据库连接池配置:
- `DATABASE_POOL_SIZE`: 10
- `DATABASE_MAX_OVERFLOW`: 20

Redis 连接池:
- 最大连接数: 20

## 安全配置

### 生产环境检查清单

- [ ] 修改 `JWT_SECRET_KEY`
- [ ] 设置 `APP_ENV=production`
- [ ] 设置 `APP_DEBUG=false`
- [ ] 配置 HTTPS
- [ ] 启用 Rate Limiting
- [ ] 配置 CORS 白名单

### 密钥管理

推荐使用环境变量或密钥管理服务:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose ps postgres

   # 查看日志
   docker-compose logs postgres
   ```

2. **Redis 连接失败**
   ```bash
   # 测试 Redis 连接
   redis-cli ping
   ```

3. **API Key 无效**
   - 检查 `DASHSCOPE_API_KEY` 是否正确
   - 确认 API Key 未过期

### 日志查看

```bash
# 查看应用日志
docker-compose logs -f app

# 查看所有服务日志
docker-compose logs -f
```

## 备份与恢复

### 数据库备份

```bash
# 备份
docker-compose exec postgres pg_dump -U postgres fitness_agent > backup.sql

# 恢复
docker-compose exec -T postgres psql -U postgres fitness_agent < backup.sql
```

### Redis 备份

```bash
# 触发 RDB 快照
docker-compose exec redis redis-cli BGSAVE

# 复制备份文件
docker cp fitness-redis:/data/dump.rdb ./redis_backup.rdb
```

## 扩展部署

### 水平扩展

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 3
```

### 负载均衡

推荐使用 Nginx 或 Traefik:

```nginx
upstream fitness_agent {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://fitness_agent;
    }
}
```

## CI/CD 配置

示例 GitHub Actions 工作流:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push
        run: |
          docker build -t fitness-agent:${{ github.sha }} .
          docker push fitness-agent:${{ github.sha }}
      - name: Deploy
        run: |
          kubectl set image deployment/fitness-agent app=fitness-agent:${{ github.sha }}
```
