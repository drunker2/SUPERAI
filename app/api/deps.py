"""
API 依赖注入模块

统一管理所有 FastAPI 依赖
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)

# ==================== 认证相关 ====================

security = HTTPBearer(auto_error=False)


async def get_request_id(
    request: Request,
    x_request_id: Annotated[str | None, Header()] = None,
) -> str:
    """
    获取或生成请求 ID

    优先使用请求头中的 X-Request-ID，否则生成新的 UUID
    """
    import uuid

    request_id = x_request_id or str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:
    """
    获取当前用户（可选）

    如果提供了有效的 Bearer Token，返回用户信息
    否则返回 None（允许匿名访问）
    """
    if credentials is None:
        return None

    token = credentials.credentials

    # 开发环境允许测试 token
    if settings.is_development and token == "test_token":
        return {"user_id": "test_user", "username": "test"}

    # 生产环境验证 JWT
    from app.auth.service import get_auth_service

    auth_service = get_auth_service()
    token_data = auth_service.decode_token(token)

    if token_data is None:
        return None

    return {"user_id": token_data.user_id, "username": token_data.username}


async def require_auth(
    user: Annotated[dict | None, Depends(get_current_user)],
) -> dict:
    """
    要求用户认证

    如果用户未登录，抛出 401 异常
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ==================== 客户端信息 ====================


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    # 优先检查代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 直接连接
    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str:
    """获取 User-Agent"""
    return request.headers.get("User-Agent", "unknown")


# ==================== 数据库会话 ====================


async def get_db():
    """
    获取数据库会话

    用于 FastAPI 依赖注入
    """
    from app.db.database import async_session_maker

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ==================== 类型别名 ====================

# 简化依赖注入的类型别名
RequestId = Annotated[str, Depends(get_request_id)]
CurrentUser = Annotated[dict | None, Depends(get_current_user)]
RequiredUser = Annotated[dict, Depends(require_auth)]
ClientIP = Annotated[str, Depends(get_client_ip)]
UserAgent = Annotated[str, Depends(get_user_agent)]
DBSession = Annotated[object, Depends(get_db)]
