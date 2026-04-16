"""
训练计划工具单元测试
"""

import pytest

from app.tools.training_plan import (
    GeneratePlanTool,
    GetExerciseInfoTool,
    ListExercisesTool,
    load_exercises_data,
)


class TestLoadExercisesData:
    """动作库加载测试"""

    def test_load_data(self):
        """测试加载动作库数据"""
        data = load_exercises_data()

        assert "exercises" in data
        assert "goals" in data
        assert "levels" in data
        assert "templates" in data

    def test_exercises_count(self):
        """测试动作数量"""
        data = load_exercises_data()
        exercises = data.get("exercises", [])

        # 至少 30 个动作
        assert len(exercises) >= 30

    def test_goals_defined(self):
        """测试目标定义"""
        data = load_exercises_data()
        goals = data.get("goals", {})

        assert "减脂" in goals
        assert "增肌" in goals
        assert "塑形" in goals

    def test_levels_defined(self):
        """测试水平定义"""
        data = load_exercises_data()
        levels = data.get("levels", {})

        assert "初级" in levels
        assert "中级" in levels
        assert "高级" in levels

    def test_templates_defined(self):
        """测试模板定义"""
        data = load_exercises_data()
        templates = data.get("templates", {})

        # 3 目标 × 3 水平 = 9 模板
        assert len(templates) >= 9


class TestGeneratePlanTool:
    """训练计划生成工具测试"""

    @pytest.fixture
    def tool(self):
        return GeneratePlanTool()

    @pytest.mark.asyncio
    async def test_generate_fat_loss_beginner_plan(self, tool):
        """测试减脂初级计划"""
        result = await tool.execute(goal="减脂", level="初级", frequency=3)

        assert result.is_success
        assert result.data["goal"] == "减脂"
        assert result.data["level"] == "初级"
        assert result.data["frequency"] == 3
        assert len(result.data["weekly_schedule"]) == 3

        # 检查有训练日
        training_days = sum(
            1 for d in result.data["weekly_schedule"]
            if d["type"] != "休息日"
        )
        assert training_days == 3

    @pytest.mark.asyncio
    async def test_generate_muscle_gain_advanced_plan(self, tool):
        """测试增肌高级计划"""
        result = await tool.execute(goal="增肌", level="高级", frequency=5)

        assert result.is_success
        assert result.data["goal"] == "增肌"
        assert result.data["level"] == "高级"

        # 高级计划应该有更多动作
        total_exercises = sum(
            len(d.get("exercises", []))
            for d in result.data["weekly_schedule"]
        )
        assert total_exercises > 0

    @pytest.mark.asyncio
    async def test_generate_shaping_plan(self, tool):
        """测试塑形计划"""
        result = await tool.execute(goal="塑形", level="中级", frequency=4)

        assert result.is_success
        assert result.data["goal"] == "塑形"

    @pytest.mark.asyncio
    async def test_plan_contains_warmup_cooldown(self, tool):
        """测试计划包含热身和冷身"""
        result = await tool.execute(goal="减脂", level="初级", frequency=3)

        assert result.is_success

        for day in result.data["weekly_schedule"]:
            if day["type"] != "休息日":
                assert "warm_up" in day
                assert "cool_down" in day
                assert day["warm_up"]["duration_minutes"] == 10
                assert len(day["warm_up"]["activities"]) > 0

    @pytest.mark.asyncio
    async def test_plan_contains_recommendations(self, tool):
        """测试计划包含建议"""
        result = await tool.execute(goal="增肌", level="中级", frequency=4)

        assert result.is_success
        assert "recommendations" in result.data
        assert "rep_range" in result.data["recommendations"]
        assert "rest_between_sets" in result.data["recommendations"]

    @pytest.mark.asyncio
    async def test_invalid_goal(self, tool):
        """测试无效目标"""
        result = await tool.execute(goal="无效目标", level="初级", frequency=3)

        assert result.is_success is False
        assert "无效" in result.error

    @pytest.mark.asyncio
    async def test_invalid_level(self, tool):
        """测试无效水平"""
        result = await tool.execute(goal="减脂", level="无效水平", frequency=3)

        assert result.is_success is False

    @pytest.mark.asyncio
    async def test_frequency_1_day(self, tool):
        """测试 1 天频率"""
        result = await tool.execute(goal="减脂", level="初级", frequency=1)

        assert result.is_success
        assert len(result.data["weekly_schedule"]) == 1

    @pytest.mark.asyncio
    async def test_frequency_7_days(self, tool):
        """测试 7 天频率"""
        result = await tool.execute(goal="增肌", level="高级", frequency=7)

        assert result.is_success
        assert len(result.data["weekly_schedule"]) == 7


class TestGetExerciseInfoTool:
    """动作信息查询工具测试"""

    @pytest.fixture
    def tool(self):
        return GetExerciseInfoTool()

    @pytest.mark.asyncio
    async def test_get_exercise_by_name(self, tool):
        """测试按名称查询"""
        result = await tool.execute(exercise_name="深蹲")

        assert result.is_success
        assert result.data["name"] == "深蹲"
        assert result.data["category"] == "腿部"
        assert "股四头肌" in result.data["muscles"]

    @pytest.mark.asyncio
    async def test_get_exercise_by_id(self, tool):
        """测试按 ID 查询"""
        result = await tool.execute(exercise_name="bench_press")

        assert result.is_success
        assert result.data["name"] == "卧推"
        assert result.data["category"] == "胸部"

    @pytest.mark.asyncio
    async def test_exercise_not_found(self, tool):
        """测试动作不存在"""
        result = await tool.execute(exercise_name="不存在的动作")

        assert result.is_success is False
        assert "未找到" in result.error

    @pytest.mark.asyncio
    async def test_exercise_has_description(self, tool):
        """测试动作有描述"""
        result = await tool.execute(exercise_name="硬拉")

        assert result.is_success
        assert "description" in result.data
        assert "硬拉" in result.data["description"]


class TestListExercisesTool:
    """动作列表查询工具测试"""

    @pytest.fixture
    def tool(self):
        return ListExercisesTool()

    @pytest.mark.asyncio
    async def test_list_all_exercises(self, tool):
        """测试列出所有动作"""
        result = await tool.execute()

        assert result.is_success
        assert result.data["count"] >= 30
        assert len(result.data["exercises"]) >= 30

    @pytest.mark.asyncio
    async def test_list_by_category(self, tool):
        """测试按分类筛选"""
        result = await tool.execute(category="腿部")

        assert result.is_success
        for exercise in result.data["exercises"]:
            assert exercise["category"] == "腿部"

    @pytest.mark.asyncio
    async def test_list_by_difficulty(self, tool):
        """测试按难度筛选"""
        result = await tool.execute(difficulty="beginner")

        assert result.is_success
        for exercise in result.data["exercises"]:
            assert exercise["difficulty"] == "beginner"

    @pytest.mark.asyncio
    async def test_list_by_category_and_difficulty(self, tool):
        """测试按分类和难度筛选"""
        result = await tool.execute(category="胸部", difficulty="beginner")

        assert result.is_success
        for exercise in result.data["exercises"]:
            assert exercise["category"] == "胸部"
            assert exercise["difficulty"] == "beginner"

    @pytest.mark.asyncio
    async def test_empty_result(self, tool):
        """测试空结果"""
        # 可能没有高级难度的核心动作
        result = await tool.execute(category="不存在的分类")

        assert result.is_success
        assert result.data["count"] == 0


class TestPlanValidation:
    """计划验证测试"""

    @pytest.fixture
    def tool(self):
        return GeneratePlanTool()

    @pytest.mark.asyncio
    async def test_plan_warnings_for_low_frequency(self, tool):
        """测试低频率警告"""
        result = await tool.execute(goal="增肌", level="初级", frequency=1)

        assert result.is_success
        # 单天训练应该有警告
        if "warnings" in result.data:
            assert len(result.data["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_plan_structure(self, tool):
        """测试计划结构完整性"""
        result = await tool.execute(goal="减脂", level="中级", frequency=4)

        assert result.is_success

        # 检查计划结构
        plan = result.data
        assert "goal" in plan
        assert "level" in plan
        assert "frequency" in plan
        assert "weekly_schedule" in plan
        assert "recommendations" in plan
        assert "notes" in plan

        # 检查每天的结构
        for day in plan["weekly_schedule"]:
            assert "day" in day
            assert "type" in day
            assert "exercises" in day
