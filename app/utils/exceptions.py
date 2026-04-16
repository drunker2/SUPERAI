"""
异常定义模块

定义应用中使用的所有自定义异常，提供统一的错误处理机制
"""

from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class FitnessAgentError(Exception):
    """
    健身助手基础异常

    所有业务异常都应该继承此类

    Attributes:
        message: 错误信息
        code: 错误码
        details: 错误详情
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


def raises(*exceptions: type[Exception]):
    """
    标记函数可能抛出的异常

    用于文档和类型提示，不影响运行时行为

    Usage:
        @raises(ValueError, TypeError)
        def parse_data(data: str) -> dict:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== LLM 相关异常 ====================


class LLMError(FitnessAgentError):
    """LLM 基础异常"""

    pass


class LLMConnectionError(LLMError):
    """LLM 连接异常"""

    def __init__(self, message: str = "LLM 服务连接失败", **kwargs: Any):
        super().__init__(message, code="LLM_CONNECTION_ERROR", **kwargs)


class LLMTimeoutError(LLMError):
    """LLM 超时异常"""

    def __init__(self, message: str = "LLM 服务响应超时", **kwargs: Any):
        super().__init__(message, code="LLM_TIMEOUT_ERROR", **kwargs)


class LLMRateLimitError(LLMError):
    """LLM 限流异常"""

    def __init__(self, message: str = "LLM 服务请求过于频繁", **kwargs: Any):
        super().__init__(message, code="LLM_RATE_LIMIT_ERROR", **kwargs)


class LLMAuthenticationError(LLMError):
    """LLM 认证异常"""

    def __init__(self, message: str = "LLM API Key 无效或已过期", **kwargs: Any):
        super().__init__(message, code="LLM_AUTH_ERROR", **kwargs)


class LLMContentFilterError(LLMError):
    """LLM 内容过滤异常"""

    def __init__(self, message: str = "内容不符合安全规范", **kwargs: Any):
        super().__init__(message, code="LLM_CONTENT_FILTER_ERROR", **kwargs)


# ==================== 工具相关异常 ====================


class ToolError(FitnessAgentError):
    """工具基础异常"""

    pass


class ToolNotFoundError(ToolError):
    """工具不存在异常"""

    def __init__(self, tool_name: str, **kwargs: Any):
        super().__init__(
            f"工具 '{tool_name}' 不存在",
            code="TOOL_NOT_FOUND",
            details={"tool_name": tool_name, **kwargs},
        )


class ToolValidationError(ToolError):
    """工具参数验证异常"""

    def __init__(self, tool_name: str, errors: list[dict[str, Any]], **kwargs: Any):
        super().__init__(
            f"工具 '{tool_name}' 参数验证失败",
            code="TOOL_VALIDATION_ERROR",
            details={"tool_name": tool_name, "errors": errors, **kwargs},
        )


class ToolExecutionError(ToolError):
    """工具执行异常"""

    def __init__(self, tool_name: str, reason: str, **kwargs: Any):
        super().__init__(
            f"工具 '{tool_name}' 执行失败: {reason}",
            code="TOOL_EXECUTION_ERROR",
            details={"tool_name": tool_name, "reason": reason, **kwargs},
        )


# ==================== MCP 相关异常 ====================


class MCPError(FitnessAgentError):
    """MCP 基础异常"""

    pass


class MCPConnectionError(MCPError):
    """MCP 连接异常"""

    def __init__(self, service_name: str, **kwargs: Any):
        super().__init__(
            f"MCP 服务 '{service_name}' 连接失败",
            code="MCP_CONNECTION_ERROR",
            details={"service_name": service_name, **kwargs},
        )


class MCPTimeoutError(MCPError):
    """MCP 超时异常"""

    def __init__(self, service_name: str, **kwargs: Any):
        super().__init__(
            f"MCP 服务 '{service_name}' 响应超时",
            code="MCP_TIMEOUT_ERROR",
            details={"service_name": service_name, **kwargs},
        )


# ==================== RAG 相关异常 ====================


class RAGError(FitnessAgentError):
    """RAG 基础异常"""

    pass


class RAGIndexError(RAGError):
    """RAG 索引异常"""

    def __init__(self, message: str = "知识库索引操作失败", **kwargs: Any):
        super().__init__(message, code="RAG_INDEX_ERROR", **kwargs)


class RAGRetrievalError(RAGError):
    """RAG 检索异常"""

    def __init__(self, message: str = "知识库检索失败", **kwargs: Any):
        super().__init__(message, code="RAG_RETRIEVAL_ERROR", **kwargs)


# ==================== 认证相关异常 ====================


class AuthenticationError(FitnessAgentError):
    """认证基础异常"""

    pass


class InvalidTokenError(AuthenticationError):
    """无效 Token 异常"""

    def __init__(self, message: str = "无效的认证令牌", **kwargs: Any):
        super().__init__(message, code="INVALID_TOKEN", **kwargs)


class TokenExpiredError(AuthenticationError):
    """Token 过期异常"""

    def __init__(self, message: str = "认证令牌已过期", **kwargs: Any):
        super().__init__(message, code="TOKEN_EXPIRED", **kwargs)


# ==================== 业务相关异常 ====================


class ValidationError(FitnessAgentError):
    """数据验证异常"""

    def __init__(self, message: str, field: str | None = None, **kwargs: Any):
        details = {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class ResourceNotFoundError(FitnessAgentError):
    """资源不存在异常"""

    def __init__(self, resource_type: str, resource_id: str, **kwargs: Any):
        super().__init__(
            f"{resource_type} '{resource_id}' 不存在",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id, **kwargs},
        )


class RateLimitExceededError(FitnessAgentError):
    """请求限流异常"""

    def __init__(
        self, retry_after: int = 60, message: str = "请求过于频繁，请稍后重试"
    ):
        super().__init__(
            message,
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after
