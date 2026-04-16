"""
路由节点单元测试
"""

import pytest

from app.agent import (
    IntentType,
    RouteType,
    create_initial_state,
    update_state_intent,
)
from app.agent.nodes import (
    router_node,
    route_decision,
    get_route_for_intent,
    INTENT_ROUTE_MAP,
)


class TestIntentRouteMap:
    """路由映射表测试"""

    def test_all_intents_have_route(self):
        """测试所有意图都有对应的路由"""
        # 所有意图类型
        all_intents = {e.value for e in IntentType}

        # 映射表中的意图
        mapped_intents = set(INTENT_ROUTE_MAP.keys())

        # 检查是否覆盖所有意图
        assert all_intents == mapped_intents, f"Missing routes for: {all_intents - mapped_intents}"

    def test_all_routes_valid(self):
        """测试所有路由都是有效类型"""
        valid_routes = {e.value for e in RouteType}

        for intent, route in INTENT_ROUTE_MAP.items():
            assert route in valid_routes, f"Invalid route '{route}' for intent '{intent}'"

    def test_fitness_consult_routes_to_knowledge(self):
        """测试健身咨询路由到知识库"""
        assert INTENT_ROUTE_MAP[IntentType.FITNESS_CONSULT.value] == RouteType.KNOWLEDGE.value

    def test_plan_request_routes_to_tool(self):
        """测试训练计划请求路由到工具"""
        assert INTENT_ROUTE_MAP[IntentType.PLAN_REQUEST.value] == RouteType.TOOL.value

    def test_body_metrics_routes_to_tool(self):
        """测试身体指标路由到工具"""
        assert INTENT_ROUTE_MAP[IntentType.BODY_METRICS.value] == RouteType.TOOL.value

    def test_nutrition_consult_routes_to_knowledge(self):
        """测试营养咨询路由到知识库"""
        assert INTENT_ROUTE_MAP[IntentType.NUTRITION_CONSULT.value] == RouteType.KNOWLEDGE.value

    def test_exercise_guide_routes_to_mcp(self):
        """测试动作指导路由到 MCP"""
        assert INTENT_ROUTE_MAP[IntentType.EXERCISE_GUIDE.value] == RouteType.MCP.value

    def test_data_record_routes_to_mcp(self):
        """测试数据记录路由到 MCP"""
        assert INTENT_ROUTE_MAP[IntentType.DATA_RECORD.value] == RouteType.MCP.value

    def test_chitchat_routes_to_chat(self):
        """测试闲聊路由到直接对话"""
        assert INTENT_ROUTE_MAP[IntentType.CHITCHAT.value] == RouteType.CHAT.value

    def test_unknown_routes_to_chat(self):
        """测试未知意图路由到直接对话（默认路由）"""
        assert INTENT_ROUTE_MAP[IntentType.UNKNOWN.value] == RouteType.CHAT.value


class TestGetRouteForIntent:
    """get_route_for_intent 函数测试"""

    def test_get_route_for_valid_intent(self):
        """测试获取有效意图的路由"""
        assert get_route_for_intent("fitness_consult") == "knowledge"
        assert get_route_for_intent("plan_request") == "tool"
        assert get_route_for_intent("chitchat") == "chat"

    def test_get_route_for_invalid_intent(self):
        """测试获取无效意图的路由（应返回默认 chat）"""
        assert get_route_for_intent("invalid_intent") == "chat"
        assert get_route_for_intent("random_string") == "chat"


class TestRouterNode:
    """router_node 函数测试"""

    def test_router_node_with_fitness_consult(self):
        """测试健身咨询的路由"""
        state = create_initial_state("怎么练腹肌", "test-session")
        update_state_intent(state, "fitness_consult", 0.95, {})

        result = router_node(state)

        assert result["route"] == "knowledge"

    def test_router_node_with_plan_request(self):
        """测试训练计划请求的路由"""
        state = create_initial_state("帮我制定计划", "test-session")
        update_state_intent(state, "plan_request", 0.98, {})

        result = router_node(state)

        assert result["route"] == "tool"

    def test_router_node_with_chitchat(self):
        """测试闲聊的路由"""
        state = create_initial_state("你好", "test-session")
        update_state_intent(state, "chitchat", 0.99, {})

        result = router_node(state)

        assert result["route"] == "chat"

    def test_router_node_with_unknown(self):
        """测试未知意图的路由（默认路由）"""
        state = create_initial_state("???", "test-session")
        update_state_intent(state, "unknown", 0.3, {})

        result = router_node(state)

        assert result["route"] == "chat"

    def test_router_node_without_intent(self):
        """测试没有意图时的默认路由"""
        state = create_initial_state("test", "test-session")

        result = router_node(state)

        assert result["route"] == "chat"


class TestRouteDecision:
    """route_decision 函数测试"""

    def test_route_decision_knowledge(self):
        """测试 knowledge 路由决策"""
        state = create_initial_state("test", "test-session")
        state["route"] = "knowledge"

        result = route_decision(state)

        assert result == "retriever"

    def test_route_decision_tool(self):
        """测试 tool 路由决策"""
        state = create_initial_state("test", "test-session")
        state["route"] = "tool"

        result = route_decision(state)

        assert result == "tool_executor"

    def test_route_decision_mcp(self):
        """测试 mcp 路由决策"""
        state = create_initial_state("test", "test-session")
        state["route"] = "mcp"

        result = route_decision(state)

        assert result == "mcp_executor"

    def test_route_decision_chat(self):
        """测试 chat 路由决策"""
        state = create_initial_state("test", "test-session")
        state["route"] = "chat"

        result = route_decision(state)

        assert result == "generator"

    def test_route_decision_default(self):
        """测试默认路由决策"""
        state = create_initial_state("test", "test-session")
        # 没有 route 字段

        result = route_decision(state)

        assert result == "generator"
