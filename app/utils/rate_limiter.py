"""
内存限流器
简单的滑动窗口限流实现
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """
    内存滑动窗口限流器

    特点:
    - 线程安全
    - 滑动窗口算法
    - 自动清理过期记录
    """

    def __init__(
        self,
        requests_per_period: int = 60,
        period_seconds: int = 60,
        cleanup_interval: int = 100,
    ):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.cleanup_interval = cleanup_interval

        # key -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._request_count = 0

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """
        检查是否允许请求

        Args:
            key: 限流键 (如 IP 地址)

        Returns:
            (是否允许, 剩余配额, 重置时间秒数)
        """
        now = time.time()
        window_start = now - self.period_seconds

        with self._lock:
            # 清理过期记录
            self._request_count += 1
            if self._request_count >= self.cleanup_interval:
                self._cleanup_expired(window_start)
                self._request_count = 0

            # 获取当前窗口内的请求数
            requests = self._requests[key]
            # 过滤掉窗口外的请求
            requests[:] = [t for t in requests if t > window_start]

            current_count = len(requests)

            if current_count >= self.requests_per_period:
                # 计算重置时间
                oldest = min(requests) if requests else now
                reset_in = int(oldest + self.period_seconds - now) + 1
                return False, 0, max(reset_in, 1)

            # 记录本次请求
            requests.append(now)
            remaining = self.requests_per_period - current_count - 1
            return True, remaining, self.period_seconds

    def _cleanup_expired(self, window_start: float) -> None:
        """清理过期的请求记录"""
        expired_keys = []
        for key, requests in self._requests.items():
            requests[:] = [t for t in requests if t > window_start]
            if not requests:
                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]

    def get_stats(self) -> dict:
        """获取限流器统计信息"""
        with self._lock:
            return {
                "total_keys": len(self._requests),
                "requests_per_period": self.requests_per_period,
                "period_seconds": self.period_seconds,
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    基于 IP 地址的滑动窗口限流
    """

    def __init__(self, app, rate_limiter: InMemoryRateLimiter | None = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or InMemoryRateLimiter(
            requests_per_period=settings.rate_limit_requests,
            period_seconds=settings.rate_limit_period,
        )

    async def dispatch(self, request: Request, call_next: Callable):
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)

        # 只对特定路径限流
        if not self._should_rate_limit(request):
            return await call_next(request)

        # 检查限流
        allowed, remaining, reset_in = self.rate_limiter.is_allowed(client_ip)

        # 设置响应头
        response = await call_next(request) if allowed else None

        if not allowed:
            logger.warning(
                "请求被限流",
                client_ip=client_ip,
                path=request.url.path,
                reset_in=reset_in,
            )
            from fastapi.responses import JSONResponse

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "请求过于频繁，请稍后重试",
                    "retry_after": reset_in,
                },
            )
            response.headers["Retry-After"] = str(reset_in)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_period)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(reset_in)
        else:
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_period)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(self.rate_limiter.period_seconds)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _should_rate_limit(self, request: Request) -> bool:
        """判断是否需要限流"""
        # 对话接口需要限流
        rate_limit_paths = ["/chat"]
        return any(request.url.path.startswith(path) for path in rate_limit_paths)


# 全局限流器实例
_rate_limiter: InMemoryRateLimiter | None = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """获取限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter
