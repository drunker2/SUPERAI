"""
日志工具模块
使用 structlog 实现结构化日志
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def setup_logging() -> None:
    """配置结构化日志"""

    # 共享处理器
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # 根据配置选择输出格式
    if settings.log_format == "json":
        # JSON 格式 - 生产环境
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        # 文本格式 - 开发环境
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # 配置 structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    获取日志器

    Args:
        name: 日志器名称，通常使用 __name__

    Returns:
        配置好的 structlog 日志器
    """
    return structlog.get_logger(name)


class LogContext:
    """日志上下文管理器"""

    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs

    def __enter__(self) -> "LogContext":
        structlog.contextvars.bind_contextvars(**self.kwargs)
        return self

    def __exit__(self, *args: Any) -> None:
        for key in self.kwargs:
            structlog.contextvars.unbind_contextvars(key)


def bind_context(**kwargs: Any) -> None:
    """绑定日志上下文"""
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """解绑日志上下文"""
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """清空日志上下文"""
    structlog.contextvars.clear_contextvars()
