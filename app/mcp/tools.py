"""
MCP 工具包装器

将 MCP 服务工具包装为 Agent 可调用的工具
"""

import asyncio
from typing import Any

from app.tools.base import BaseTool, ToolParameterSchema, ToolResult
from app.utils import get_logger

logger = get_logger(__name__)


class MCPExerciseInfoTool(BaseTool):
    """
    MCP 动作信息查询工具

    通过 MCP 服务查询动作详情
    """

    name = "mcp_exercise_info"
    description = "通过 MCP 服务查询健身动作的详细信息"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="exercise_name",
            type="string",
            description="动作名称",
            required=True,
        ),
    ]

    timeout = 10.0

    async def execute(self, exercise_name: str) -> ToolResult:
        """执行 MCP 工具调用"""
        try:
            from app.mcp.client import get_mcp_client

            pool = get_mcp_client()
            result = await pool.call_tool(
                service_name="exercise",
                tool_name="get_exercise_info",
                arguments={"exercise_name": exercise_name},
            )

            if "error" in result:
                return ToolResult.error(result["error"])

            return ToolResult.success(result)

        except Exception as e:
            logger.error("MCP 工具执行失败", error=str(e))
            return ToolResult.error(f"MCP 服务调用失败: {e}")


class MCPSearchExercisesTool(BaseTool):
    """
    MCP 动作搜索工具

    通过 MCP 服务搜索动作
    """

    name = "mcp_search_exercises"
    description = "通过 MCP 服务搜索符合条件的健身动作"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="query",
            type="string",
            description="搜索关键词",
            required=False,
        ),
        ToolParameterSchema(
            name="category",
            type="string",
            description="动作分类",
            required=False,
        ),
        ToolParameterSchema(
            name="difficulty",
            type="string",
            description="难度级别",
            required=False,
        ),
    ]

    timeout = 10.0

    async def execute(
        self,
        query: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
    ) -> ToolResult:
        """执行 MCP 工具调用"""
        try:
            from app.mcp.client import get_mcp_client

            pool = get_mcp_client()
            result = await pool.call_tool(
                service_name="exercise",
                tool_name="search_exercises",
                arguments={
                    k: v for k, v in {
                        "query": query,
                        "category": category,
                        "difficulty": difficulty,
                    }.items() if v
                },
            )

            if "error" in result:
                return ToolResult.error(result["error"])

            return ToolResult.success(result)

        except Exception as e:
            logger.error("MCP 工具执行失败", error=str(e))
            return ToolResult.error(f"MCP 服务调用失败: {e}")


def register_mcp_tools() -> None:
    """注册 MCP 工具"""
    from app.tools.registry import register_tool

    # 注册 MCP 包装工具
    register_tool(MCPExerciseInfoTool())
    register_tool(MCPSearchExercisesTool())

    logger.info("MCP 工具已注册")


# 同步包装函数（用于直接调用）
def get_exercise_info_sync(exercise_name: str) -> dict[str, Any]:
    """
    同步方式获取动作信息

    直接从动作库获取，不通过 MCP 服务
    """
    import json
    from pathlib import Path

    data_dir = Path(__file__).parent.parent / "data"
    exercises_file = data_dir / "exercises.json"

    if not exercises_file.exists():
        return {"error": "动作库文件不存在"}

    with open(exercises_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for exercise in data.get("exercises", []):
        if (
            exercise["name"] == exercise_name
            or exercise["id"] == exercise_name.lower().replace(" ", "_")
        ):
            return {
                "id": exercise["id"],
                "name": exercise["name"],
                "category": exercise["category"],
                "type": exercise["type"],
                "difficulty": exercise["difficulty"],
                "muscles": exercise["muscles"],
                "equipment": exercise["equipment"],
            }

    return {"error": f"未找到动作: {exercise_name}"}


def search_exercises_sync(
    query: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """
    同步方式搜索动作

    直接从动作库搜索，不通过 MCP 服务
    """
    import json
    from pathlib import Path

    data_dir = Path(__file__).parent.parent / "data"
    exercises_file = data_dir / "exercises.json"

    if not exercises_file.exists():
        return {"error": "动作库文件不存在", "count": 0, "exercises": []}

    with open(exercises_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for exercise in data.get("exercises", []):
        if category and exercise.get("category") != category:
            continue
        if difficulty and exercise.get("difficulty") != difficulty:
            continue
        if query:
            query_lower = query.lower()
            if (
                query_lower not in exercise["name"].lower()
                and query_lower not in exercise.get("category", "").lower()
                and not any(query_lower in m.lower() for m in exercise.get("muscles", []))
            ):
                continue

        results.append({
            "id": exercise["id"],
            "name": exercise["name"],
            "category": exercise["category"],
            "difficulty": exercise["difficulty"],
            "muscles": exercise["muscles"],
        })

    return {
        "count": len(results),
        "exercises": results,
    }
