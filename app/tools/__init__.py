"""
工具系统模块
"""

from app.tools.base import BaseTool, ToolResult, ToolError
from app.tools.registry import ToolRegistry, get_tool_registry, register_tool
from app.tools.fitness import (
    CalculateBMITool,
    CalculateBMRTool,
    CalculateBodyFatTool,
    register_fitness_tools,
)
from app.tools.training_plan import (
    GeneratePlanTool,
    GetExerciseInfoTool,
    ListExercisesTool,
    register_training_tools,
)

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolError",
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "CalculateBMITool",
    "CalculateBMRTool",
    "CalculateBodyFatTool",
    "register_fitness_tools",
    "GeneratePlanTool",
    "GetExerciseInfoTool",
    "ListExercisesTool",
    "register_training_tools",
]
