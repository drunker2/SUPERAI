"""
健身计算工具

包含 BMI、BMR 等身体指标计算工具
"""

from typing import Any

from app.tools.base import BaseTool, ToolParameterSchema, ToolResult
from app.utils import get_logger

logger = get_logger(__name__)


class CalculateBMITool(BaseTool):
    """
    BMI 计算工具

    根据身高体重计算 BMI 指数并给出健康建议
    """

    name = "calculate_bmi"
    description = "根据身高和体重计算 BMI (身体质量指数)，返回 BMI 值、分类和健康建议"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="height",
            type="number",
            description="身高 (厘米)",
            required=True,
            minimum=50,
            maximum=300,
        ),
        ToolParameterSchema(
            name="weight",
            type="number",
            description="体重 (公斤)",
            required=True,
            minimum=20,
            maximum=500,
        ),
    ]

    async def execute(self, height: float, weight: float) -> ToolResult:
        """
        计算 BMI

        Args:
            height: 身高 (厘米)
            weight: 体重 (公斤)

        Returns:
            ToolResult: 包含 BMI 值、分类和建议
        """
        try:
            # 计算 BMI
            height_m = height / 100  # 转换为米
            bmi = round(weight / (height_m ** 2), 2)

            # 确定分类
            if bmi < 18.5:
                category = "偏瘦"
                advice = "建议适当增加营养摄入，进行力量训练增加肌肉量。"
            elif bmi < 24:
                category = "正常"
                advice = "体重在健康范围内，建议保持均衡饮食和规律运动。"
            elif bmi < 28:
                category = "超重"
                advice = "建议控制饮食热量，增加有氧运动，每周至少 150 分钟中等强度运动。"
            elif bmi < 32:
                category = "肥胖"
                advice = "建议咨询医生或营养师，制定科学的减重计划，循序渐进。"
            else:
                category = "重度肥胖"
                advice = "建议尽快就医，在专业指导下进行体重管理。"

            result = {
                "bmi": bmi,
                "category": category,
                "advice": advice,
                "height": height,
                "weight": weight,
            }

            logger.info("BMI 计算完成", height=height, weight=weight, bmi=bmi, category=category)

            return ToolResult.success(result, metadata={"unit": "kg/m²"})

        except Exception as e:
            logger.error("BMI 计算失败", error=str(e), height=height, weight=weight)
            return ToolResult.error(f"BMI 计算失败: {e}")


class CalculateBMRTool(BaseTool):
    """
    BMR 计算工具

    使用 Mifflin-St Jeor 公式计算基础代谢率
    """

    name = "calculate_bmr"
    description = "根据身高、体重、年龄和性别计算 BMR (基础代谢率)，返回每日基础消耗热量"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="weight",
            type="number",
            description="体重 (公斤)",
            required=True,
            minimum=20,
            maximum=500,
        ),
        ToolParameterSchema(
            name="height",
            type="number",
            description="身高 (厘米)",
            required=True,
            minimum=50,
            maximum=300,
        ),
        ToolParameterSchema(
            name="age",
            type="integer",
            description="年龄 (岁)",
            required=True,
            minimum=1,
            maximum=120,
        ),
        ToolParameterSchema(
            name="gender",
            type="string",
            description="性别",
            required=True,
            enum=["male", "female", "男", "女"],
        ),
    ]

    async def execute(
        self,
        weight: float,
        height: float,
        age: int,
        gender: str,
    ) -> ToolResult:
        """
        计算 BMR (Mifflin-St Jeor 公式)

        男性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄 + 5
        女性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄 - 161

        Args:
            weight: 体重 (公斤)
            height: 身高 (厘米)
            age: 年龄 (岁)
            gender: 性别 ("male"/"female"/"男"/"女")

        Returns:
            ToolResult: 包含 BMR 值和建议
        """
        try:
            # 标准化性别输入
            is_male = gender.lower() in ("male", "男")

            # Mifflin-St Jeor 公式
            bmr = 10 * weight + 6.25 * height - 5 * age
            if is_male:
                bmr += 5
            else:
                bmr -= 161

            bmr = round(bmr, 0)

            # 计算不同活动水平下的每日消耗
            activity_levels = {
                "久坐": bmr * 1.2,
                "轻度活动": bmr * 1.375,
                "中度活动": bmr * 1.55,
                "高度活动": bmr * 1.725,
                "极高活动": bmr * 1.9,
            }

            result = {
                "bmr": int(bmr),
                "unit": "kcal/day",
                "gender": "男" if is_male else "女",
                "daily_needs": {
                    level: int(round(calories, 0))
                    for level, calories in activity_levels.items()
                },
            }

            logger.info(
                "BMR 计算完成",
                weight=weight,
                height=height,
                age=age,
                gender=gender,
                bmr=bmr,
            )

            return ToolResult.success(result)

        except Exception as e:
            logger.error("BMR 计算失败", error=str(e))
            return ToolResult.error(f"BMR 计算失败: {e}")


class CalculateBodyFatTool(BaseTool):
    """
    体脂率估算工具

    使用美国海军方法估算体脂率
    """

    name = "calculate_body_fat"
    description = "根据身高、体重、腰围、年龄和性别估算体脂率"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="height",
            type="number",
            description="身高 (厘米)",
            required=True,
            minimum=50,
            maximum=300,
        ),
        ToolParameterSchema(
            name="waist",
            type="number",
            description="腰围 (厘米)",
            required=True,
            minimum=40,
            maximum=200,
        ),
        ToolParameterSchema(
            name="neck",
            type="number",
            description="颈围 (厘米)",
            required=True,
            minimum=20,
            maximum=80,
        ),
        ToolParameterSchema(
            name="hip",
            type="number",
            description="臀围 (厘米)，女性必填",
            required=False,
            minimum=50,
            maximum=200,
        ),
        ToolParameterSchema(
            name="gender",
            type="string",
            description="性别",
            required=True,
            enum=["male", "female", "男", "女"],
        ),
    ]

    async def execute(
        self,
        height: float,
        waist: float,
        neck: float,
        gender: str,
        hip: float | None = None,
    ) -> ToolResult:
        """
        估算体脂率 (美国海军方法)

        男性: 体脂率 = 495 / (1.0324 - 0.19077×log10(腰围-颈围) + 0.15456×log10(身高)) - 450
        女性: 体脂率 = 495 / (1.29579 - 0.35004×log10(腰围+臀围-颈围) + 0.22100×log10(身高)) - 450

        Args:
            height: 身高 (厘米)
            waist: 腰围 (厘米)
            neck: 颈围 (厘米)
            gender: 性别
            hip: 臀围 (厘米)，女性必填

        Returns:
            ToolResult: 包含体脂率估算值
        """
        import math

        try:
            is_male = gender.lower() in ("male", "男")

            if not is_male and hip is None:
                return ToolResult.error("女性用户需要提供臀围数据")

            if is_male:
                # 男性公式
                body_fat = 495 / (
                    1.0324
                    - 0.19077 * math.log10(waist - neck)
                    + 0.15456 * math.log10(height)
                ) - 450
            else:
                # 女性公式
                body_fat = 495 / (
                    1.29579
                    - 0.35004 * math.log10(waist + hip - neck)
                    + 0.22100 * math.log10(height)
                ) - 450

            body_fat = round(body_fat, 1)

            # 确定分类
            if is_male:
                if body_fat < 6:
                    category = "必需脂肪"
                elif body_fat < 14:
                    category = "运动员"
                elif body_fat < 18:
                    category = "健康"
                elif body_fat < 25:
                    category = "可接受"
                else:
                    category = "肥胖"
            else:
                if body_fat < 14:
                    category = "必需脂肪"
                elif body_fat < 21:
                    category = "运动员"
                elif body_fat < 25:
                    category = "健康"
                elif body_fat < 32:
                    category = "可接受"
                else:
                    category = "肥胖"

            result = {
                "body_fat_percent": body_fat,
                "category": category,
                "gender": "男" if is_male else "女",
            }

            logger.info("体脂率估算完成", body_fat=body_fat, category=category)

            return ToolResult.success(result)

        except Exception as e:
            logger.error("体脂率估算失败", error=str(e))
            return ToolResult.error(f"体脂率估算失败: {e}")


# 注册工具实例
def register_fitness_tools() -> None:
    """注册健身计算工具"""
    from app.tools.registry import register_tool

    register_tool(CalculateBMITool())
    register_tool(CalculateBMRTool())
    register_tool(CalculateBodyFatTool())

    logger.info("健身计算工具已注册")
