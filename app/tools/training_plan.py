"""
训练计划生成工具
"""

import json
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool, ToolParameterSchema, ToolResult
from app.utils import get_logger

logger = get_logger(__name__)

# 动作库数据路径
DATA_DIR = Path(__file__).parent.parent / "data"
EXERCISES_FILE = DATA_DIR / "exercises.json"


def load_exercises_data() -> dict[str, Any]:
    """加载动作库数据"""
    if not EXERCISES_FILE.exists():
        logger.error(f"动作库文件不存在: {EXERCISES_FILE}")
        return {"exercises": [], "goals": {}, "levels": {}, "templates": {}}

    with open(EXERCISES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class GeneratePlanTool(BaseTool):
    """
    训练计划生成工具

    根据用户目标、水平和训练频率生成个性化训练计划
    """

    name = "generate_plan"
    description = "根据用户目标(减脂/增肌/塑形)、水平(初级/中级/高级)和每周训练天数生成个性化训练计划"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="goal",
            type="string",
            description="训练目标",
            required=True,
            enum=["减脂", "增肌", "塑形"],
        ),
        ToolParameterSchema(
            name="level",
            type="string",
            description="健身水平",
            required=True,
            enum=["初级", "中级", "高级"],
        ),
        ToolParameterSchema(
            name="frequency",
            type="integer",
            description="每周训练天数 (1-7)",
            required=True,
            minimum=1,
            maximum=7,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._data = load_exercises_data()

    def _get_exercise_by_id(self, exercise_id: str) -> dict[str, Any] | None:
        """根据 ID 获取动作信息"""
        for exercise in self._data.get("exercises", []):
            if exercise["id"] == exercise_id:
                return exercise
        return None

    def _get_goal_config(self, goal: str) -> dict[str, Any]:
        """获取目标配置"""
        return self._data.get("goals", {}).get(goal, {})

    def _get_level_config(self, level: str) -> dict[str, Any]:
        """获取水平配置"""
        return self._data.get("levels", {}).get(level, {})

    def _get_template(self, goal: str, level: str) -> dict[str, Any]:
        """获取训练模板"""
        template_key = f"{goal}_{level}"
        return self._data.get("templates", {}).get(template_key, {})

    def _generate_daily_plan(
        self,
        day_index: int,
        day_type: str,
        exercise_ids: list[str],
        goal_config: dict[str, Any],
        level_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        生成单日训练计划

        Args:
            day_index: 天数索引 (1-7)
            day_type: 训练类型描述
            exercise_ids: 动作 ID 列表
            goal_config: 目标配置
            level_config: 水平配置

        Returns:
            单日计划
        """
        if "休息" in day_type:
            return {
                "day": day_index,
                "type": "休息日",
                "exercises": [],
                "notes": ["充分休息", "保证睡眠", "补充蛋白质"],
            }

        # 获取动作详情
        exercises = []
        rep_range = goal_config.get("rep_range", [10, 15])
        rest_time = goal_config.get("rest_time", 60)

        for i, exercise_id in enumerate(exercise_ids[:level_config.get("exercises_per_day", 6)]):
            exercise_info = self._get_exercise_by_id(exercise_id)
            if exercise_info:
                exercises.append({
                    "order": i + 1,
                    "name": exercise_info["name"],
                    "category": exercise_info["category"],
                    "sets": 3 + (1 if level_config.get("use_advanced", False) else 0),
                    "reps": f"{rep_range[0]}-{rep_range[1]}",
                    "rest_seconds": rest_time,
                    "difficulty": exercise_info["difficulty"],
                    "muscles": exercise_info["muscles"],
                })

        # 有氧运动处理
        cardio_exercises = []
        cardio_ratio = goal_config.get("cardio_ratio", 0.2)
        if cardio_ratio > 0 and "有氧" not in day_type:
            # 非有氧日也加入少量有氧
            pass
        elif "有氧" in day_type or "HIIT" in day_type:
            cardio_exercises.append({
                "order": len(exercises) + 1,
                "name": "有氧运动",
                "type": "cardio",
                "duration_minutes": 20 if goal_config.get("cardio_ratio", 0) > 0.3 else 15,
                "intensity": "中等" if goal_config.get("cardio_ratio", 0) < 0.4 else "高强度",
            })

        return {
            "day": day_index,
            "type": day_type,
            "exercises": exercises,
            "cardio": cardio_exercises,
            "warm_up": {
                "duration_minutes": 10,
                "activities": ["动态拉伸", "关节活动", "轻度有氧热身"],
            },
            "cool_down": {
                "duration_minutes": 5,
                "activities": ["静态拉伸", "泡沫轴放松"],
            },
        }

    def _validate_plan(self, plan: dict[str, Any]) -> list[str]:
        """
        验证计划的合理性

        Args:
            plan: 生成的计划

        Returns:
            警告信息列表
        """
        warnings = []

        # 检查训练日数量
        training_days = sum(1 for d in plan["weekly_schedule"] if d["type"] != "休息日")
        if training_days < 2:
            warnings.append("训练日较少，建议至少每周训练 2-3 天")
        elif training_days > 6:
            warnings.append("训练日较多，注意充分休息恢复")

        # 检查是否有休息日
        if training_days == 7:
            warnings.append("没有休息日，建议每周至少安排 1 天休息")

        # 检查动作多样性
        all_categories = set()
        for day in plan["weekly_schedule"]:
            for exercise in day.get("exercises", []):
                all_categories.add(exercise.get("category", ""))

        if len(all_categories) < 3 and training_days >= 3:
            warnings.append("动作类型较少，建议增加动作多样性")

        return warnings

    async def execute(self, goal: str, level: str, frequency: int) -> ToolResult:
        """
        生成训练计划

        Args:
            goal: 训练目标 (减脂/增肌/塑形)
            level: 健身水平 (初级/中级/高级)
            frequency: 每周训练天数 (1-7)

        Returns:
            ToolResult: 包含完整训练计划
        """
        try:
            # 获取配置
            goal_config = self._get_goal_config(goal)
            level_config = self._get_level_config(level)
            template = self._get_template(goal, level)

            if not goal_config:
                return ToolResult.error(f"无效的训练目标: {goal}")
            if not level_config:
                return ToolResult.error(f"无效的健身水平: {level}")

            # 获取模板中的日结构
            day_structure = template.get("day_structure", ["全身训练"] * 7)
            exercise_ids = template.get("exercises", [])

            # 根据频率调整计划
            # 如果用户频率低于模板天数，选择最重要的训练日
            adjusted_structure = day_structure[:frequency]
            if frequency < len(day_structure):
                # 优先保留力量训练日，减少休息日
                training_days = [d for d in day_structure if "休息" not in d]
                rest_days = [d for d in day_structure if "休息" in d]
                adjusted_structure = training_days[:frequency]

                # 如果训练日不够，用其他训练填充
                while len(adjusted_structure) < frequency:
                    adjusted_structure.append(training_days[len(adjusted_structure) % len(training_days)])

            # 生成每周计划
            weekly_schedule = []
            for i, day_type in enumerate(adjusted_structure):
                daily_plan = self._generate_daily_plan(
                    day_index=i + 1,
                    day_type=day_type,
                    exercise_ids=exercise_ids,
                    goal_config=goal_config,
                    level_config=level_config,
                )
                weekly_schedule.append(daily_plan)

            # 构建完整计划
            plan = {
                "goal": goal,
                "level": level,
                "frequency": frequency,
                "goal_description": goal_config.get("description", ""),
                "level_description": level_config.get("description", ""),
                "weekly_schedule": weekly_schedule,
                "recommendations": {
                    "rep_range": goal_config.get("rep_range", [10, 15]),
                    "rest_between_sets": f"{goal_config.get('rest_time', 60)}秒",
                    "cardio_ratio": f"{int(goal_config.get('cardio_ratio', 0.2) * 100)}%",
                    "progression": "每2周增加5-10%的训练量",
                },
                "notes": [
                    "训练前充分热身，训练后做好拉伸",
                    "注意动作标准，避免受伤",
                    "配合合理饮食，效果更佳",
                    "如有不适，请立即停止并咨询专业人士",
                ],
            }

            # 验证计划
            warnings = self._validate_plan(plan)
            if warnings:
                plan["warnings"] = warnings

            logger.info(
                "训练计划生成完成",
                goal=goal,
                level=level,
                frequency=frequency,
                training_days=sum(1 for d in weekly_schedule if d["type"] != "休息日"),
            )

            return ToolResult.success(plan)

        except Exception as e:
            logger.error("训练计划生成失败", error=str(e), goal=goal, level=level)
            return ToolResult.error(f"训练计划生成失败: {e}")


class GetExerciseInfoTool(BaseTool):
    """
    动作信息查询工具

    获取动作库中的动作详情
    """

    name = "get_exercise_info"
    description = "根据动作名称或ID查询动作的详细信息，包括目标肌群、难度、器械要求等"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="exercise_name",
            type="string",
            description="动作名称或ID",
            required=True,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._data = load_exercises_data()

    async def execute(self, exercise_name: str) -> ToolResult:
        """
        查询动作信息

        Args:
            exercise_name: 动作名称或ID

        Returns:
            ToolResult: 动作详情
        """
        try:
            exercise_name_lower = exercise_name.lower()

            for exercise in self._data.get("exercises", []):
                if (
                    exercise["id"] == exercise_name_lower
                    or exercise["name"] == exercise_name
                ):
                    return ToolResult.success({
                        "id": exercise["id"],
                        "name": exercise["name"],
                        "category": exercise["category"],
                        "type": exercise["type"],
                        "difficulty": exercise["difficulty"],
                        "muscles": exercise["muscles"],
                        "equipment": exercise["equipment"],
                        "description": self._get_exercise_description(exercise),
                    })

            return ToolResult.error(f"未找到动作: {exercise_name}")

        except Exception as e:
            logger.error("动作查询失败", error=str(e))
            return ToolResult.error(f"动作查询失败: {e}")

    def _get_exercise_description(self, exercise: dict) -> str:
        """生成动作描述"""
        muscles = "、".join(exercise["muscles"])
        return (
            f"{exercise['name']}是一个{exercise['type']}类动作，"
            f"主要锻炼{muscles}，"
            f"难度为{exercise['difficulty']}，"
            f"需要{exercise['equipment']}。"
        )


class ListExercisesTool(BaseTool):
    """
    动作列表查询工具

    按分类或难度筛选动作
    """

    name = "list_exercises"
    description = "获取动作列表，可按分类、难度筛选"
    version = "1.0.0"

    parameters = [
        ToolParameterSchema(
            name="category",
            type="string",
            description="动作分类 (腿部/胸部/背部/肩部/手臂/核心/有氧)",
            required=False,
        ),
        ToolParameterSchema(
            name="difficulty",
            type="string",
            description="难度 (beginner/intermediate/advanced)",
            required=False,
            enum=["beginner", "intermediate", "advanced"],
        ),
    ]

    def __init__(self):
        super().__init__()
        self._data = load_exercises_data()

    async def execute(
        self,
        category: str | None = None,
        difficulty: str | None = None,
    ) -> ToolResult:
        """
        获取动作列表

        Args:
            category: 动作分类
            difficulty: 难度

        Returns:
            ToolResult: 动作列表
        """
        try:
            exercises = self._data.get("exercises", [])

            # 筛选
            if category:
                exercises = [e for e in exercises if e["category"] == category]
            if difficulty:
                exercises = [e for e in exercises if e["difficulty"] == difficulty]

            result = {
                "count": len(exercises),
                "filters": {
                    "category": category,
                    "difficulty": difficulty,
                },
                "exercises": [
                    {
                        "id": e["id"],
                        "name": e["name"],
                        "category": e["category"],
                        "difficulty": e["difficulty"],
                        "muscles": e["muscles"],
                    }
                    for e in exercises
                ],
            }

            return ToolResult.success(result)

        except Exception as e:
            logger.error("动作列表查询失败", error=str(e))
            return ToolResult.error(f"动作列表查询失败: {e}")


def register_training_tools() -> None:
    """注册训练计划相关工具"""
    from app.tools.registry import register_tool

    register_tool(GeneratePlanTool())
    register_tool(GetExerciseInfoTool())
    register_tool(ListExercisesTool())

    logger.info("训练计划工具已注册")
