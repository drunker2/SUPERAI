"""
MCP 模块测试
"""

import pytest

from app.mcp.tools import get_exercise_info_sync, search_exercises_sync


class TestMCPToolsSync:
    """MCP 工具同步函数测试"""

    def test_get_exercise_info_found(self):
        """测试获取存在的动作信息"""
        result = get_exercise_info_sync("深蹲")

        assert "error" not in result
        assert result["name"] == "深蹲"
        assert result["category"] == "腿部"
        assert "股四头肌" in result["muscles"]

    def test_get_exercise_info_by_id(self):
        """测试通过 ID 获取动作信息"""
        result = get_exercise_info_sync("bench_press")

        assert "error" not in result
        assert result["name"] == "卧推"

    def test_get_exercise_info_not_found(self):
        """测试获取不存在的动作"""
        result = get_exercise_info_sync("不存在的动作")

        assert "error" in result
        assert "未找到" in result["error"]

    def test_search_exercises_by_category(self):
        """测试按分类搜索"""
        result = search_exercises_sync(category="腿部")

        assert result["count"] > 0
        for exercise in result["exercises"]:
            assert exercise["category"] == "腿部"

    def test_search_exercises_by_difficulty(self):
        """测试按难度搜索"""
        result = search_exercises_sync(difficulty="beginner")

        assert result["count"] > 0
        for exercise in result["exercises"]:
            assert exercise["difficulty"] == "beginner"

    def test_search_exercises_by_query(self):
        """测试关键词搜索"""
        result = search_exercises_sync(query="深蹲")

        assert result["count"] >= 1
        found_names = [e["name"] for e in result["exercises"]]
        assert "深蹲" in found_names

    def test_search_exercises_combined(self):
        """测试组合条件搜索"""
        result = search_exercises_sync(
            category="胸部",
            difficulty="intermediate"
        )

        assert result["count"] >= 0
        for exercise in result["exercises"]:
            assert exercise["category"] == "胸部"
            assert exercise["difficulty"] == "intermediate"

    def test_search_exercises_empty_result(self):
        """测试空结果"""
        result = search_exercises_sync(category="不存在的分类")

        assert result["count"] == 0
        assert result["exercises"] == []


class TestMCPServerTools:
    """MCP 服务端工具测试"""

    @pytest.fixture
    def server(self):
        from app.mcp.server import ExerciseMCPServer
        return ExerciseMCPServer()

    def test_get_exercise_info_tool(self, server):
        """测试服务端获取动作信息"""
        result = server._get_exercise_info("深蹲")

        assert "error" not in result
        assert result["name"] == "深蹲"

    def test_search_exercises_tool(self, server):
        """测试服务端搜索"""
        result = server._search_exercises(category="腿部")

        assert result["count"] > 0

    def test_list_by_category_tool(self, server):
        """测试服务端按分类列出"""
        result = server._list_by_category("背部")

        assert result["count"] > 0


class TestMCPToolsWrapper:
    """MCP 工具包装器测试"""

    @pytest.fixture
    def exercise_tool(self):
        from app.mcp.tools import MCPExerciseInfoTool
        return MCPExerciseInfoTool()

    @pytest.fixture
    def search_tool(self):
        from app.mcp.tools import MCPSearchExercisesTool
        return MCPSearchExercisesTool()

    def test_tool_definition(self, exercise_tool):
        """测试工具定义"""
        assert exercise_tool.name == "mcp_exercise_info"
        assert "MCP" in exercise_tool.description
        assert len(exercise_tool.parameters) == 1

    def test_search_tool_definition(self, search_tool):
        """测试搜索工具定义"""
        assert search_tool.name == "mcp_search_exercises"
        assert len(search_tool.parameters) == 3
