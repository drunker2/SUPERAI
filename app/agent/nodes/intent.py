"""
意图识别节点
"""

import json
import re
import time
from typing import Any

from app.agent.prompts.intent import get_intent_messages
from app.agent.state import (
    AgentState,
    IntentType,
    update_state_intent,
    update_state_error,
)
from app.llm import QwenLLM, LLMResponse, QwenAPIError
from app.utils import get_logger, bind_context

logger = get_logger(__name__)

# 置信度阈值
CONFIDENCE_THRESHOLD = 0.5

# LLM 实例
_llm: QwenLLM | None = None


def get_llm() -> QwenLLM:
    """获取 LLM 实例"""
    global _llm
    if _llm is None:
        _llm = QwenLLM()
    return _llm


def parse_intent_response(content: str) -> dict[str, Any]:
    """
    解析 LLM 返回的意图识别结果

    Args:
        content: LLM 返回的内容

    Returns:
        解析后的意图字典，包含 intent, confidence, entities
    """
    # 方法1: 尝试直接解析整个内容为 JSON
    try:
        result = json.loads(content.strip())
        return {
            "intent": result.get("intent", "unknown"),
            "confidence": float(result.get("confidence", 0.5)),
            "entities": result.get("entities", {}),
        }
    except (json.JSONDecodeError, ValueError):
        pass

    # 方法2: 尝试提取 JSON 对象（支持嵌套）
    # 找到第一个 { 和最后一个 }
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(content[start:end+1])
            return {
                "intent": result.get("intent", "unknown"),
                "confidence": float(result.get("confidence", 0.5)),
                "entities": result.get("entities", {}),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON 解析失败: {e}")

    # 方法3: 使用正则提取关键字段
    # 匹配 "intent": "value" 或 intent: "value" 或 intent: value
    intent_patterns = [
        r'"intent"\s*:\s*"([\w_]+)"',
        r'intent\s*:\s*"([\w_]+)"',
        r'intent\s*:\s*([\w_]+)',
    ]

    intent = "unknown"
    for pattern in intent_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            intent = match.group(1)
            break

    # 匹配置信度
    confidence_patterns = [
        r'"confidence"\s*:\s*([\d.]+)',
        r'confidence\s*:\s*([\d.]+)',
    ]

    confidence = 0.5
    for pattern in confidence_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                confidence = float(match.group(1))
            except ValueError:
                pass
            break

    # 尝试提取 entities
    entities = {}
    entities_match = re.search(r'"entities"\s*:\s*(\{[^{}]*\})', content)
    if entities_match:
        try:
            entities = json.loads(entities_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    return {
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
    }


def validate_intent(intent: str) -> str:
    """
    验证意图类型是否有效

    Args:
        intent: 意图字符串

    Returns:
        有效的意图类型
    """
    valid_intents = {e.value for e in IntentType}

    if intent in valid_intents:
        return intent

    # 尝试模糊匹配
    intent_lower = intent.lower().replace("-", "_")
    for valid_intent in valid_intents:
        if intent_lower == valid_intent:
            return valid_intent

    return IntentType.UNKNOWN.value


async def intent_node(state: AgentState) -> AgentState:
    """
    意图识别节点

    分析用户输入，识别意图类型、置信度和实体

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态
    """
    query = state["query"]
    session_id = state["session_id"]

    bind_context(node="intent", session_id=session_id, query_length=len(query))

    start_time = time.perf_counter()
    logger.info("开始意图识别", query=query[:50])

    try:
        llm = get_llm()

        # 获取意图识别的系统提示词
        from app.agent.prompts.intent import INTENT_RECOGNITION_PROMPT, INTENT_RECOGNITION_USER_TEMPLATE

        # 构建用户消息
        user_prompt = INTENT_RECOGNITION_USER_TEMPLATE.format(query=query)

        # 调用 LLM
        response: LLMResponse = await llm.ainvoke(
            prompt=user_prompt,
            system_prompt=INTENT_RECOGNITION_PROMPT,
        )

        # 解析意图
        parsed = parse_intent_response(response.content)
        intent = validate_intent(parsed["intent"])
        confidence = parsed["confidence"]
        entities = parsed["entities"]

        # 置信度低于阈值时，标记为 unknown
        if confidence < CONFIDENCE_THRESHOLD:
            logger.info(
                "置信度低于阈值，标记为 unknown",
                original_intent=intent,
                confidence=confidence,
                threshold=CONFIDENCE_THRESHOLD,
            )
            intent = IntentType.UNKNOWN.value

        # 更新状态
        update_state_intent(state, intent, confidence, entities)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "意图识别完成",
            intent=intent,
            confidence=confidence,
            entities=entities,
            duration_ms=round(duration_ms, 2),
        )

        return state

    except QwenAPIError as e:
        logger.error("LLM 调用失败", error=str(e))
        update_state_error(state, f"意图识别失败: {e}")
        update_state_intent(state, IntentType.UNKNOWN.value, 0.0, {})
        return state

    except Exception as e:
        logger.exception("意图识别异常", error=str(e))
        update_state_error(state, f"意图识别异常: {e}")
        update_state_intent(state, IntentType.UNKNOWN.value, 0.0, {})
        return state


def intent_node_sync(state: AgentState) -> AgentState:
    """
    意图识别节点（同步版本）

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态
    """
    import asyncio

    # 在新的事件循环中运行异步函数
    return asyncio.run(intent_node(state))
