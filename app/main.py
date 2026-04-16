"""
FastAPI 应用入口
"""

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.utils import (
    FitnessAgentError,
    RateLimitExceededError,
    RateLimitMiddleware,
    setup_logging,
    get_logger,
    bind_context,
)

logger = get_logger(__name__)


# ==================== 响应模型 ====================


class ErrorResponse(BaseModel):
    """统一错误响应模型"""

    code: str
    message: str
    trace_id: str | None = None
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str
    version: str
    environment: str


# ==================== 生命周期管理 ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logging()

    # 注册工具
    from app.tools import register_fitness_tools, register_training_tools
    register_fitness_tools()
    register_training_tools()

    logger.info(
        "应用启动",
        app_name=settings.app_name,
        environment=settings.app_env,
        version="1.0.0",
    )

    yield

    # 关闭时
    logger.info("应用关闭")


# ==================== 创建应用 ====================


app = FastAPI(
    title="Fitness Agent",
    description="""
## 智能健身助手 API

基于大语言模型的智能健身助手，提供专业的健身咨询、训练计划生成、身体指标计算等功能。

### 核心功能

| 模块 | 说明 |
|------|------|
| 💬 **智能对话** | 多轮对话、上下文记忆、流式响应 |
| 📊 **身体指标** | BMI、BMR、体脂率计算 |
| 📋 **训练计划** | 个性化训练计划生成 |
| 📚 **知识检索** | RAG 语义搜索健身知识 |
| 🔐 **用户管理** | JWT 认证、用户画像 |

### API 端点

| 路径 | 说明 |
|------|------|
| `/auth/*` | 用户认证相关 |
| `/chat/*` | 对话相关 |
| `/tools/*` | 工具查询 |
| `/metrics` | Prometheus 监控 |

### 认证方式

所有需要认证的接口使用 JWT Bearer Token：

```
Authorization: Bearer <access_token>
```

### 技术栈

- **Web 框架**: FastAPI
- **Agent 框架**: LangGraph
- **LLM**: 通义千问 (Qwen)
- **向量数据库**: ChromaDB
- **缓存/会话**: Redis
- **监控**: Prometheus + Grafana
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Fitness Agent Team",
        "email": "support@fitness-agent.example.com",
    },
    license_info={
        "name": "MIT License",
    },
)


# ==================== 中间件配置 ====================


# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 限流中间件
app.add_middleware(RateLimitMiddleware)


# 请求日志中间件
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.perf_counter()
    trace_id = request.headers.get("X-Request-ID") or request.state.request_id if hasattr(request.state, "request_id") else ""

    # 绑定日志上下文
    bind_context(trace_id=trace_id, path=request.url.path, method=request.method)

    logger.info("请求开始")

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "请求完成",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # 添加响应头
        response.headers["X-Request-ID"] = trace_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "请求异常",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2),
        )
        raise


# ==================== 异常处理 ====================


@app.exception_handler(FitnessAgentError)
async def fitness_agent_error_handler(request: Request, exc: FitnessAgentError):
    """业务异常处理"""
    trace_id = getattr(request.state, "request_id", None)

    logger.warning(
        "业务异常",
        error_code=exc.code,
        error_message=exc.message,
        details=exc.details,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            trace_id=trace_id,
            details=exc.details if exc.details else None,
        ).model_dump(),
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError):
    """限流异常处理"""
    trace_id = getattr(request.state, "request_id", None)

    logger.warning("请求被限流", retry_after=exc.retry_after)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            trace_id=trace_id,
        ).model_dump(),
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """参数验证异常处理"""
    trace_id = getattr(request.state, "request_id", None)

    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning("参数验证失败", errors=errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="请求参数验证失败",
            trace_id=trace_id,
            details={"errors": errors},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    trace_id = getattr(request.state, "request_id", None)

    logger.exception(
        "未处理的异常",
        error=str(exc),
        error_type=type(exc).__name__,
    )

    # 生产环境不暴露具体错误信息
    message = "服务器内部错误" if settings.is_production else str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message=message,
            trace_id=trace_id,
        ).model_dump(),
    )


# ==================== 路由 ====================


@app.get(
    "/health",
    tags=["系统"],
    summary="健康检查",
    description="""
检查服务是否正常运行。

## 检查项
- 应用状态
- Redis 连接状态

## 用途
- 负载均衡健康检查
- Kubernetes liveness/readiness 探针
- 监控系统状态检测
""",
    responses={
        200: {
            "description": "服务正常",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "version": "1.0.0",
                        "environment": "production",
                        "redis": "ok",
                    }
                }
            }
        },
        503: {
            "description": "服务异常",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "version": "1.0.0",
                        "environment": "production",
                        "redis": "error",
                    }
                }
            }
        },
    },
)
async def health_check():
    """健康检查接口"""
    from app.agent.memory import get_redis_session_manager

    # 检查 Redis 连接
    redis_status = "ok"
    try:
        manager = get_redis_session_manager()
        result = manager.health_check()
        if result["status"] != "ok":
            redis_status = "error"
    except Exception:
        redis_status = "error"

    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.app_env,
        "redis": redis_status,
    }


@app.get(
    "/",
    tags=["系统"],
    summary="根路径",
    description="""
返回 API 基本信息。

## 返回内容
- 应用名称
- 版本号
- 文档地址
- 健康检查地址
""",
    responses={
        200: {
            "description": "API 基本信息",
            "content": {
                "application/json": {
                    "example": {
                        "name": "fitness-agent",
                        "version": "1.0.0",
                        "docs": "/docs",
                        "health": "/health",
                    }
                }
            }
        },
    },
)
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# 注册业务路由
from app.api.routes import (
    chat_router,
    tools_router,
    auth_router,
    stream_router,
    metrics_router,
)

# 业务路由（注意：各路由模块已定义前缀）
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(tools_router)
app.include_router(stream_router)
app.include_router(metrics_router)
