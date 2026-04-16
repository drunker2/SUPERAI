"""
MCP 服务模块
"""

from app.mcp.server import ExerciseMCPServer, create_server
from app.mcp.client import MCPClient, MCPServicePool, get_mcp_client
from app.mcp.tools import (
    MCPExerciseInfoTool,
    MCPSearchExercisesTool,
    register_mcp_tools,
    get_exercise_info_sync,
    search_exercises_sync,
)

__all__ = [
    "ExerciseMCPServer",
    "create_server",
    "MCPClient",
    "MCPServicePool",
    "get_mcp_client",
    "MCPExerciseInfoTool",
    "MCPSearchExercisesTool",
    "register_mcp_tools",
    "get_exercise_info_sync",
    "search_exercises_sync",
]
