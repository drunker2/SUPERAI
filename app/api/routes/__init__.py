"""
API 路由模块
"""

from app.api.routes.chat import router as chat_router
from app.api.routes.tools import router as tools_router
from app.api.routes.auth import router as auth_router
from app.api.routes.stream import router as stream_router
from app.api.routes.metrics import router as metrics_router

__all__ = ["chat_router", "tools_router", "auth_router", "stream_router", "metrics_router"]
