"""
统一 API 响应格式
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    统一 API 响应格式

    所有 API 接口都应该返回这个格式
    """

    code: int = Field(default=0, description="状态码，0 表示成功")
    message: str = Field(default="success", description="状态信息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str | None = Field(default=None, description="追踪 ID")

    @classmethod
    def success(cls, data: T, message: str = "success", trace_id: str | None = None) -> "APIResponse[T]":
        """创建成功响应"""
        return cls(code=0, message=message, data=data, trace_id=trace_id)

    @classmethod
    def error(
        cls,
        code: int,
        message: str,
        trace_id: str | None = None,
    ) -> "APIResponse[None]":
        """创建错误响应"""
        return cls(code=code, message=message, data=None, trace_id=trace_id)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应格式
    """

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页数量")
    has_more: bool = Field(default=False, description="是否有更多")


class ErrorResponse(BaseModel):
    """
    错误响应格式
    """

    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    trace_id: str | None = Field(default=None, description="追踪 ID")
    details: dict[str, Any] | None = Field(default=None, description="错误详情")


# 常用错误码定义
class ErrorCode:
    """错误码定义"""

    # 通用错误
    UNKNOWN = 1000
    INVALID_REQUEST = 1001
    RATE_LIMITED = 1002

    # 认证错误
    UNAUTHORIZED = 2001
    TOKEN_EXPIRED = 2002
    TOKEN_INVALID = 2003
    PERMISSION_DENIED = 2004

    # 业务错误
    SESSION_NOT_FOUND = 3001
    TOOL_NOT_FOUND = 3002
    LLM_ERROR = 3003
    RAG_ERROR = 3004

    # 数据错误
    VALIDATION_ERROR = 4001
    DATA_NOT_FOUND = 4002
    DATA_EXISTS = 4003
