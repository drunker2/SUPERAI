"""
工具系统单元测试
"""

import pytest

from app.tools.base import BaseTool, ToolParameterSchema, ToolResult, ToolStatus, ToolError
from app.tools.registry import ToolRegistry, get_tool_registry
from app.tools.fitness import (
    CalculateBMITool,
    CalculateBMRTool,
    CalculateBodyFatTool,
    register_fitness_tools,
)


class TestToolResult:
    """ToolResult 测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = ToolResult.success({"value": 100})
        assert result.is_success is True
        assert result.status == ToolStatus.SUCCESS
        assert result.data == {"value": 100}

    def test_error_result(self):
        """测试错误结果"""
        result = ToolResult.error("出错了")
        assert result.is_success is False
        assert result.status == ToolStatus.ERROR
        assert result.error == "出错了"

    def test_to_dict(self):
        """测试转换为字典"""
        result = ToolResult.success({"bmi": 22.5}, metadata={"unit": "kg/m²"})
        d = result.to_dict()
        assert d["status"] == "success"
        assert d["data"]["bmi"] == 22.5
        assert d["metadata"]["unit"] == "kg/m²"


class TestToolParameterSchema:
    """ToolParameterSchema 测试"""

    def test_required_parameter(self):
        """测试必填参数"""
        param = ToolParameterSchema(
            name="height",
            type="number",
            description="身高",
            required=True,
        )
        assert param.required is True
        assert param.default is None

    def test_optional_parameter(self):
        """测试可选参数"""
        param = ToolParameterSchema(
            name="level",
            type="string",
            description="水平",
            required=False,
            default="beginner",
        )
        assert param.required is False
        assert param.default == "beginner"

    def test_to_openapi(self):
        """测试 OpenAPI Schema 生成"""
        param = ToolParameterSchema(
            name="weight",
            type="number",
            description="体重",
            minimum=20,
            maximum=500,
        )
        schema = param.to_openapi()
        assert schema["type"] == "number"
        assert schema["minimum"] == 20
        assert schema["maximum"] == 500


class TestBaseTool:
    """BaseTool 测试"""

    def test_tool_definition_validation(self):
        """测试工具定义验证"""
        # 缺少 name 的工具应该报错
        class InvalidTool(BaseTool):
            description = "无效工具"
            parameters = []

            async def execute(self, **kwargs):
                return ToolResult.success(None)

        with pytest.raises(ValueError):
            InvalidTool()

    def test_validate_parameters_required(self):
        """测试必填参数验证"""
        tool = CalculateBMITool()

        # 缺少必填参数
        with pytest.raises(ToolError) as exc_info:
            tool.validate_parameters({"height": 175})
        assert "缺少必填参数" in str(exc_info.value.message)

    def test_validate_parameters_type_conversion(self):
        """测试参数类型转换"""
        tool = CalculateBMITool()

        # 字符串转数字
        params = tool.validate_parameters({"height": "175", "weight": "70"})
        assert params["height"] == 175
        assert params["weight"] == 70

    def test_validate_parameters_boundary(self):
        """测试参数边界检查"""
        tool = CalculateBMITool()

        # 身高超限
        with pytest.raises(ToolError) as exc_info:
            tool.validate_parameters({"height": 500, "weight": 70})
        assert "大于最大值" in str(exc_info.value.message)

    def test_to_openai_tool(self):
        """测试 OpenAI 工具格式"""
        tool = CalculateBMITool()
        openai_tool = tool.to_openai_tool()

        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "calculate_bmi"
        assert "parameters" in openai_tool["function"]
        assert "height" in openai_tool["function"]["parameters"]["properties"]


class TestToolRegistry:
    """ToolRegistry 测试"""

    @pytest.fixture
    def registry(self):
        """创建测试用的注册器"""
        return ToolRegistry()

    def test_register_tool(self, registry):
        """测试工具注册"""
        tool = CalculateBMITool()
        registry.register(tool)

        assert registry.exists("calculate_bmi")
        assert registry.count() == 1

    def test_unregister_tool(self, registry):
        """测试工具注销"""
        tool = CalculateBMITool()
        registry.register(tool)

        result = registry.unregister("calculate_bmi")
        assert result is True
        assert not registry.exists("calculate_bmi")

    def test_get_tool(self, registry):
        """测试获取工具"""
        tool = CalculateBMITool()
        registry.register(tool)

        retrieved = registry.get("calculate_bmi")
        assert retrieved is tool

    def test_list_tools(self, registry):
        """测试工具列表"""
        registry.register(CalculateBMITool())
        registry.register(CalculateBMRTool())

        tools = registry.list_tools()
        assert len(tools) == 2
        names = registry.list_names()
        assert "calculate_bmi" in names
        assert "calculate_bmr" in names

    def test_duplicate_register(self, registry):
        """测试重复注册"""
        registry.register(CalculateBMITool())

        with pytest.raises(ValueError):
            registry.register(CalculateBMITool())


class TestCalculateBMITool:
    """BMI 计算工具测试"""

    @pytest.fixture
    def tool(self):
        return CalculateBMITool()

    @pytest.mark.asyncio
    async def test_normal_bmi(self, tool):
        """测试正常 BMI"""
        result = await tool.execute(height=175, weight=70)

        assert result.is_success
        assert result.data["bmi"] == 22.86
        assert result.data["category"] == "正常"

    @pytest.mark.asyncio
    async def test_underweight_bmi(self, tool):
        """测试偏瘦 BMI"""
        result = await tool.execute(height=180, weight=55)

        assert result.is_success
        assert result.data["category"] == "偏瘦"

    @pytest.mark.asyncio
    async def test_overweight_bmi(self, tool):
        """测试超重 BMI"""
        result = await tool.execute(height=170, weight=80)

        assert result.is_success
        assert result.data["category"] == "超重"

    @pytest.mark.asyncio
    async def test_obese_bmi(self, tool):
        """测试肥胖 BMI"""
        result = await tool.execute(height=170, weight=95)

        assert result.is_success
        assert result.data["category"] in ["肥胖", "重度肥胖"]


class TestCalculateBMRTool:
    """BMR 计算工具测试"""

    @pytest.fixture
    def tool(self):
        return CalculateBMRTool()

    @pytest.mark.asyncio
    async def test_male_bmr(self, tool):
        """测试男性 BMR"""
        # 男性, 30岁, 175cm, 70kg
        # BMR = 10 × 70 + 6.25 × 175 - 5 × 30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
        result = await tool.execute(weight=70, height=175, age=30, gender="male")

        assert result.is_success
        assert result.data["bmr"] == 1649  # 四舍五入
        assert result.data["gender"] == "男"
        assert "daily_needs" in result.data

    @pytest.mark.asyncio
    async def test_female_bmr(self, tool):
        """测试女性 BMR"""
        # 女性, 25岁, 165cm, 55kg
        # BMR = 10 × 55 + 6.25 × 165 - 5 × 25 - 161 = 550 + 1031.25 - 125 - 161 = 1295.25
        result = await tool.execute(weight=55, height=165, age=25, gender="female")

        assert result.is_success
        assert result.data["bmr"] == 1295
        assert result.data["gender"] == "女"

    @pytest.mark.asyncio
    async def test_chinese_gender_input(self, tool):
        """测试中文性别输入"""
        result = await tool.execute(weight=70, height=175, age=30, gender="男")

        assert result.is_success
        assert result.data["gender"] == "男"


class TestCalculateBodyFatTool:
    """体脂率计算工具测试"""

    @pytest.fixture
    def tool(self):
        return CalculateBodyFatTool()

    @pytest.mark.asyncio
    async def test_male_body_fat(self, tool):
        """测试男性体脂率"""
        result = await tool.execute(
            height=175,
            waist=85,
            neck=38,
            gender="male",
        )

        assert result.is_success
        assert 5 < result.data["body_fat_percent"] < 40
        assert result.data["category"] in ["必需脂肪", "运动员", "健康", "可接受", "肥胖"]

    @pytest.mark.asyncio
    async def test_female_body_fat(self, tool):
        """测试女性体脂率"""
        result = await tool.execute(
            height=165,
            waist=70,
            neck=32,
            hip=95,
            gender="female",
        )

        assert result.is_success
        assert 10 < result.data["body_fat_percent"] < 45

    @pytest.mark.asyncio
    async def test_female_missing_hip(self, tool):
        """测试女性缺少臀围"""
        result = await tool.execute(
            height=165,
            waist=70,
            neck=32,
            gender="female",
        )

        assert result.is_success is False
        assert "臀围" in result.error


class TestFitnessToolsIntegration:
    """健身工具集成测试"""

    def test_register_fitness_tools(self):
        """测试注册健身工具"""
        registry = ToolRegistry()
        registry.register(CalculateBMITool())
        registry.register(CalculateBMRTool())
        registry.register(CalculateBodyFatTool())

        assert registry.count() == 3
        assert registry.exists("calculate_bmi")
        assert registry.exists("calculate_bmr")
        assert registry.exists("calculate_body_fat")

    @pytest.mark.asyncio
    async def test_execute_bmi_via_registry(self):
        """测试通过注册器执行 BMI"""
        registry = ToolRegistry()
        registry.register(CalculateBMITool())

        result = await registry.execute("calculate_bmi", height=175, weight=70)

        assert result.is_success
        assert result.data["bmi"] == 22.86
