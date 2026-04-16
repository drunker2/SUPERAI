"""
MCP 服务端 - 动作库服务

提供健身动作查询的 MCP 服务
"""

import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.utils import get_logger

logger = get_logger(__name__)

# 动作库数据路径
DATA_DIR = Path(__file__).parent.parent / "data"
EXERCISES_FILE = DATA_DIR / "exercises.json"


def load_exercises_data() -> dict[str, Any]:
    """加载动作库数据"""
    if not EXERCISES_FILE.exists():
        return {"exercises": []}

    with open(EXERCISES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class ExerciseMCPServer:
    """
    健身动作库 MCP 服务

    提供工具:
    - get_exercise_info: 查询动作详情
    - search_exercises: 搜索动作
    - list_exercises_by_category: 按分类列出动作
    """

    def __init__(self, name: str = "fitness-exercise-server"):
        """
        初始化 MCP 服务

        Args:
            name: 服务名称
        """
        self.name = name
        self.server = Server(name)
        self._data = load_exercises_data()
        self._setup_handlers()

    def _setup_handlers(self):
        """设置 MCP 处理器"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """返回可用工具列表"""
            return [
                Tool(
                    name="get_exercise_info",
                    description="根据动作名称查询动作的详细信息，包括目标肌群、难度、器械要求等",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "exercise_name": {
                                "type": "string",
                                "description": "动作名称，如'深蹲'、'卧推'、'硬拉'",
                            }
                        },
                        "required": ["exercise_name"],
                    },
                ),
                Tool(
                    name="search_exercises",
                    description="搜索符合条件的健身动作",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词",
                            },
                            "category": {
                                "type": "string",
                                "description": "动作分类: 腿部/胸部/背部/肩部/手臂/核心/有氧",
                            },
                            "difficulty": {
                                "type": "string",
                                "description": "难度: beginner/intermediate/advanced",
                            },
                        },
                    },
                ),
                Tool(
                    name="list_exercises_by_category",
                    description="按分类列出所有动作",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "动作分类: 腿部/胸部/背部/肩部/手臂/核心/有氧",
                            }
                        },
                        "required": ["category"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """执行工具调用"""
            try:
                if name == "get_exercise_info":
                    result = self._get_exercise_info(arguments.get("exercise_name", ""))
                elif name == "search_exercises":
                    result = self._search_exercises(
                        query=arguments.get("query"),
                        category=arguments.get("category"),
                        difficulty=arguments.get("difficulty"),
                    )
                elif name == "list_exercises_by_category":
                    result = self._list_by_category(arguments.get("category", ""))
                else:
                    result = {"error": f"未知工具: {name}"}

                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

            except Exception as e:
                logger.error("MCP 工具执行失败", tool=name, error=str(e))
                return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    def _get_exercise_info(self, exercise_name: str) -> dict[str, Any]:
        """获取动作详情"""
        exercises = self._data.get("exercises", [])

        for exercise in exercises:
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
                    "tips": self._get_exercise_tips(exercise),
                }

        return {"error": f"未找到动作: {exercise_name}"}

    def _search_exercises(
        self,
        query: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
    ) -> dict[str, Any]:
        """搜索动作"""
        exercises = self._data.get("exercises", [])
        results = []

        for exercise in exercises:
            # 过滤条件
            if category and exercise.get("category") != category:
                continue
            if difficulty and exercise.get("difficulty") != difficulty:
                continue
            if query:
                # 关键词匹配
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

    def _list_by_category(self, category: str) -> dict[str, Any]:
        """按分类列出动作"""
        return self._search_exercises(category=category)

    def _get_exercise_tips(self, exercise: dict) -> list[str]:
        """获取动作提示"""
        tips = {
            "squat": [
                "膝盖与脚尖方向一致",
                "下蹲至大腿与地面平行",
                "核心收紧，背部挺直",
            ],
            "bench_press": [
                "肩胛骨下沉后缩",
                "肘部与躯干呈45度角",
                "控制杠铃下放速度",
            ],
            "deadlift": [
                "背部保持挺直",
                "杠铃贴近身体",
                "臀部和膝盖同时伸展",
            ],
        }
        return tips.get(exercise.get("id", ""), ["保持动作标准", "控制呼吸节奏"])

    async def run(self):
        """运行 MCP 服务"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def create_server() -> ExerciseMCPServer:
    """创建 MCP 服务实例"""
    return ExerciseMCPServer()


async def main():
    """主入口"""
    server = create_server()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
