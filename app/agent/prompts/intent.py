"""
意图识别 Prompt
"""

INTENT_RECOGNITION_PROMPT = """你是一个意图识别助手，负责分析用户输入并识别其意图。

## 意图类型

1. **fitness_consult** - 健身咨询
   用户询问健身相关问题，如训练方法、健身知识等

2. **plan_request** - 训练计划请求
   用户请求制定个性化的训练计划
   实体: goal(减脂/增肌/塑形), level(初级/中级/高级), frequency(每周几天)

3. **body_metrics** - 身体指标计算
   用户请求计算BMI、基础代谢、体脂率等身体指标
   实体: height(身高cm), weight(体重kg), age(年龄), gender(性别)

4. **nutrition_consult** - 营养咨询
   用户询问营养、饮食相关问题

5. **exercise_guide** - 动作指导
   用户询问具体健身动作的标准姿势和要领
   实体: exercise_name(动作名称)

6. **data_record** - 数据记录
   用户请求记录训练数据或运动记录

7. **chitchat** - 闲聊
   日常问候或与健身无关的对话

8. **unknown** - 未知意图
   无法明确识别的用户意图

## 示例

用户: 怎么练腹肌最快
意图: fitness_consult
置信度: 0.95
实体: {"body_part": "腹肌", "goal": "练得快"}

用户: 帮我制定一个减脂计划，我每周能练3次
意图: plan_request
置信度: 0.98
实体: {"goal": "减脂", "frequency": 3, "level": "初级"}

用户: 我是新手，想增肌，每周练4天，帮我定个计划
意图: plan_request
置信度: 0.99
实体: {"goal": "增肌", "frequency": 4, "level": "初级"}

用户: 我身高175体重70，帮我算BMI
意图: body_metrics
置信度: 0.99
实体: {"height": 175, "weight": 70, "metric_type": "BMI"}

用户: 蛋白粉有用吗
意图: nutrition_consult
置信度: 0.92
实体: {"topic": "蛋白粉"}

用户: 深蹲的标准姿势是什么
意图: exercise_guide
置信度: 0.96
实体: {"exercise_name": "深蹲"}

用户: 今天跑了5公里，帮我记录一下
意图: data_record
置信度: 0.94
实体: {"exercise_type": "跑步", "distance": 5, "unit": "公里"}

用户: 你好
意图: chitchat
置信度: 0.99
实体: {}

用户: 今天天气怎么样
意图: chitchat
置信度: 0.95
实体: {}

## 输出格式

请以JSON格式输出，包含以下字段：
- intent: 意图类型（必须是上述8种之一）
- confidence: 置信度（0-1之间的小数）
- entities: 提取的实体（键值对）

## 注意事项

1. 置信度低于0.5时，intent应为unknown
2. 实体提取要准确，不要编造不存在的实体
3. 对于plan_request，必须提取goal, level, frequency实体
4. 对于body_metrics，必须提取height, weight实体
5. 只输出JSON，不要输出其他内容
"""

INTENT_RECOGNITION_USER_TEMPLATE = """请识别以下用户输入的意图：

用户: {query}

请输出JSON格式的意图识别结果：
"""


def get_intent_prompt(query: str) -> str:
    """
    获取意图识别的完整 Prompt

    Args:
        query: 用户输入

    Returns:
        完整的 Prompt 字符串
    """
    return f"{INTENT_RECOGNITION_PROMPT}\n{INTENT_RECOGNITION_USER_TEMPLATE.format(query=query)}"


def get_intent_messages(query: str) -> list[dict]:
    """
    获取意图识别的消息格式

    Args:
        query: 用户输入

    Returns:
        消息列表
    """
    return [
        {"role": "system", "content": INTENT_RECOGNITION_PROMPT},
        {"role": "user", "content": f"请识别以下用户输入的意图：\n\n用户: {query}"},
    ]
