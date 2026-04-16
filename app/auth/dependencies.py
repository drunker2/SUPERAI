"""
认证依赖注入

用于 FastAPI 路由保护
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.auth.service import get_auth_service, AuthService

# Bearer Token 安全方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | None:
    """
    获取当前用户

    从 Authorization Header 中解析 Token 并返回用户

    Args:
        credentials: Bearer Token
        db: 数据库会话
        auth_service: 认证服务

    Returns:
        用户对象或 None（未登录）
    """
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = auth_service.decode_token(token)

    if token_data is None or token_data.user_id is None:
        return None

    user = await auth_service.get_user_by_id(db, token_data.user_id)

    return user


async def get_current_active_user(
    user: Annotated[User | None, Depends(get_current_user)],
) -> User:
    """
    获取当前活跃用户（必须登录）

    Args:
        user: 当前用户

    Returns:
        活跃用户

    Raises:
        HTTPException: 未登录或用户未激活
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_superuser(
    user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    获取当前超级用户

    Args:
        user: 当前活跃用户

    Returns:
        超级用户

    Raises:
        HTTPException: 非超级用户
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )

    return user


# 可选的用户依赖（允许未登录）
OptionalUser = Annotated[User | None, Depends(get_current_user)]

# 必须登录的用户依赖
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# 超级用户依赖
SuperUser = Annotated[User, Depends(get_current_superuser)]
