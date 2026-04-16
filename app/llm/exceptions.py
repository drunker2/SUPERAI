"""
LLM 异常定义
针对通义千问 API 的特定异常
"""

from typing import Any

from app.utils.exceptions import LLMError


class QwenAPIError(LLMError):
    """通义千问 API 基础异常"""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        request_id: str | None = None,
        **kwargs: Any,
    ):
        details = {}
        if request_id:
            details["request_id"] = request_id
        details.update(kwargs)
        super().__init__(message, code=code, details=details)


class QwenAuthenticationError(QwenAPIError):
    """API Key 无效或过期"""

    def __init__(self, message: str = "API Key 无效或已过期", **kwargs: Any):
        super().__init__(message, code="QWEN_AUTH_ERROR", **kwargs)


class QwenRateLimitError(QwenAPIError):
    """请求频率超限"""

    def __init__(
        self,
        message: str = "请求频率超限，请稍后重试",
        retry_after: int | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, code="QWEN_RATE_LIMIT", **kwargs)
        self.retry_after = retry_after


class QwenModelNotFoundError(QwenAPIError):
    """模型不存在"""

    def __init__(self, model_name: str, **kwargs: Any):
        super().__init__(
            f"模型 '{model_name}' 不存在或不可用",
            code="QWEN_MODEL_NOT_FOUND",
            **kwargs,
        )


class QwenInvalidRequestError(QwenAPIError):
    """请求参数无效"""

    def __init__(self, message: str = "请求参数无效", **kwargs: Any):
        super().__init__(message, code="QWEN_INVALID_REQUEST", **kwargs)


class QwenContentFilterError(QwenAPIError):
    """内容安全过滤"""

    def __init__(self, message: str = "内容不符合安全规范，已被拦截", **kwargs: Any):
        super().__init__(message, code="QWEN_CONTENT_FILTER", **kwargs)


class QwenTimeoutError(QwenAPIError):
    """请求超时"""

    def __init__(self, message: str = "请求超时", **kwargs: Any):
        super().__init__(message, code="QWEN_TIMEOUT", **kwargs)


class QwenServiceUnavailableError(QwenAPIError):
    """服务不可用"""

    def __init__(self, message: str = "服务暂时不可用，请稍后重试", **kwargs: Any):
        super().__init__(message, code="QWEN_SERVICE_UNAVAILABLE", **kwargs)
