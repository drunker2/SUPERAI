"""
API 路由模块

提供 FastAPI 应用所需的依赖注入、响应格式和路由
"""

from app.api.deps import (
    get_request_id,
    get_current_user,
    require_auth,
    get_client_ip,
    get_user_agent,
    RequestId,
    CurrentUser,
    RequiredUser,
    ClientIP,
    UserAgent,
    DBSession,
)
from app.api.response import (
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
    ErrorCode,
)

__all__ = [
    # 依赖注入
    "get_request_id",
    "get_current_user",
    "require_auth",
    "get_client_ip",
    "get_user_agent",
    "RequestId",
    "CurrentUser",
    "RequiredUser",
    "ClientIP",
    "UserAgent",
    "DBSession",
    # 响应格式
    "APIResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "ErrorCode",
]
