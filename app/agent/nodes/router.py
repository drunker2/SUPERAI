"""
路由节点
根据意图识别结果，决定后续执行路径
"""

from app.agent.state import (
    AgentState,
    IntentType,
    RouteType,
    update_state_route,
)
from app.utils import get_logger, bind_context

logger = get_logger(__name__)


# ==================== 路由映射表 ====================

INTENT_ROUTE_MAP: dict[str, str] = {
    IntentType.FITNESS_CONSULT.value: RouteType.KNOWLEDGE.value,
    IntentType.PLAN_REQUEST.value: RouteType.TOOL.value,
    IntentType.BODY_METRICS.value: RouteType.TOOL.value,
    IntentType.NUTRITION_CONSULT.value: RouteType.KNOWLEDGE.value,
    IntentType.EXERCISE_GUIDE.value: RouteType.MCP.value,
    IntentType.DATA_RECORD.value: RouteType.MCP.value,
    IntentType.CHITCHAT.value: RouteType.CHAT.value,
    IntentType.UNKNOWN.value: RouteType.CHAT.value,  # 默认路由
}


def get_route_for_intent(intent: str) -> str:
    """
    根据意图获取路由

    Args:
        intent: 意图类型

    Returns:
        路由目标
    """
    return INTENT_ROUTE_MAP.get(intent, RouteType.CHAT.value)


def router_node(state: AgentState) -> AgentState:
    """
    路由节点

    根据意图识别结果，决定后续执行路径

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态（包含 route 字段）
    """
    session_id = state["session_id"]
    intent = state.get("intent", IntentType.UNKNOWN.value)

    bind_context(node="router", session_id=session_id, intent=intent)

    # 获取路由
    route = get_route_for_intent(intent)

    # 更新状态
    update_state_route(state, route)

    logger.info(
        "路由决策",
        intent=intent,
        route=route,
        session_id=session_id,
    )

    return state


def route_decision(state: AgentState) -> str:
    """
    路由决策函数

    用于 LangGraph 条件边，返回下一个节点名称

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点名称
    """
    route = state.get("route", RouteType.CHAT.value)

    # 路由到节点名称的映射
    route_node_map = {
        RouteType.KNOWLEDGE.value: "retriever",
        RouteType.TOOL.value: "tool_executor",
        RouteType.MCP.value: "mcp_executor",
        RouteType.CHAT.value: "generator",
    }

    node_name = route_node_map.get(route, "generator")

    logger.debug(
        "路由决策",
        route=route,
        target_node=node_name,
    )

    return node_name
