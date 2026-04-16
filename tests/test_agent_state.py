"""
Agent 状态模块单元测试
"""

import pytest

from app.agent import (
    IntentType,
    RouteType,
    NodeType,
    MessageRole,
    AgentState,
    create_initial_state,
    create_state_from_history,
    update_state_intent,
    update_state_route,
    update_state_error,
    add_tool_call,
    add_mcp_call,
    add_retrieved_docs,
    set_response,
    get_intent,
    get_route,
    has_errors,
    get_errors,
    get_tool_results,
    get_mcp_results,
    get_retrieved_docs,
    get_response,
    get_messages,
    get_user_id,
    get_session_id,
    state_to_dict,
)


class TestEnums:
    """枚举测试"""

    def test_intent_type_values(self):
        """测试意图类型枚举值"""
        assert IntentType.FITNESS_CONSULT.value == "fitness_consult"
        assert IntentType.PLAN_REQUEST.value == "plan_request"
        assert IntentType.BODY_METRICS.value == "body_metrics"
        assert IntentType.NUTRITION_CONSULT.value == "nutrition_consult"
        assert IntentType.EXERCISE_GUIDE.value == "exercise_guide"
        assert IntentType.DATA_RECORD.value == "data_record"
        assert IntentType.CHITCHAT.value == "chitchat"
        assert IntentType.UNKNOWN.value == "unknown"

    def test_route_type_values(self):
        """测试路由类型枚举值"""
        assert RouteType.KNOWLEDGE.value == "knowledge"
        assert RouteType.TOOL.value == "tool"
        assert RouteType.MCP.value == "mcp"
        assert RouteType.CHAT.value == "chat"

    def test_node_type_values(self):
        """测试节点类型枚举值"""
        assert NodeType.INTENT.value == "intent"
        assert NodeType.ROUTER.value == "router"
        assert NodeType.RETRIEVER.value == "retriever"
        assert NodeType.TOOL_EXECUTOR.value == "tool_executor"
        assert NodeType.MCP_EXECUTOR.value == "mcp_executor"
        assert NodeType.GENERATOR.value == "generator"
        assert NodeType.ERROR_HANDLER.value == "error_handler"

    def test_message_role_values(self):
        """测试消息角色枚举值"""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"


class TestCreateState:
    """状态创建测试"""

    def test_create_initial_state(self):
        """测试创建初始状态"""
        state = create_initial_state(
            query="你好",
            session_id="test-session-123",
        )

        assert state["query"] == "你好"
        assert state["session_id"] == "test-session-123"
        assert state["messages"] == []
        assert "user_id" not in state

    def test_create_initial_state_with_user_id(self):
        """测试创建带用户 ID 的初始状态"""
        state = create_initial_state(
            query="你好",
            session_id="test-session-123",
            user_id="user-001",
        )

        assert state["query"] == "你好"
        assert state["session_id"] == "test-session-123"
        assert state["user_id"] == "user-001"

    def test_create_state_from_history(self):
        """测试从历史消息创建状态"""
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]

        state = create_state_from_history(
            query="我想健身",
            session_id="test-session-456",
            history=history,
        )

        assert state["query"] == "我想健身"
        assert state["session_id"] == "test-session-456"
        assert len(state["messages"]) == 2
        assert state["messages"][0]["content"] == "你好"


class TestUpdateState:
    """状态更新测试"""

    def test_update_state_intent(self):
        """测试更新意图"""
        state = create_initial_state("怎么练腹肌", "session-1")
        update_state_intent(state, "fitness_consult", 0.95, {"body_part": "腹肌"})

        assert state["intent"] == "fitness_consult"
        assert state["intent_confidence"] == 0.95
        assert state["entities"]["body_part"] == "腹肌"

    def test_update_state_route(self):
        """测试更新路由"""
        state = create_initial_state("怎么练腹肌", "session-1")
        update_state_route(state, "knowledge")

        assert state["route"] == "knowledge"

    def test_update_state_error(self):
        """测试添加错误"""
        state = create_initial_state("test", "session-1")
        update_state_error(state, "工具调用失败")
        update_state_error(state, "重试超时")

        assert len(state["errors"]) == 2
        assert "工具调用失败" in state["errors"]

    def test_add_tool_call(self):
        """测试添加工具调用"""
        state = create_initial_state("计算 BMI", "session-1")
        add_tool_call(
            state,
            tool_name="calculate_bmi",
            tool_args={"height": 175, "weight": 70},
            tool_result={"bmi": 22.86, "category": "正常"},
        )

        assert len(state["tool_calls"]) == 1
        assert state["tool_calls"][0]["tool_name"] == "calculate_bmi"
        assert state["tool_results"][0]["result"]["bmi"] == 22.86

    def test_add_mcp_call(self):
        """测试添加 MCP 调用"""
        state = create_initial_state("深蹲动作指导", "session-1")
        add_mcp_call(
            state,
            service_name="exercise_lib",
            tool_name="get_exercise_info",
            tool_args={"exercise_name": "深蹲"},
            tool_result={"target_muscles": ["股四头肌", "臀大肌"]},
        )

        assert len(state["mcp_calls"]) == 1
        assert state["mcp_calls"][0]["service_name"] == "exercise_lib"

    def test_add_retrieved_docs(self):
        """测试添加检索文档"""
        state = create_initial_state("怎么减脂", "session-1")
        add_retrieved_docs(
            state,
            docs=[
                {"content": "减脂需要热量缺口", "score": 0.9},
                {"content": "有氧运动有助于减脂", "score": 0.85},
            ],
            scores=[0.9, 0.85],
        )

        assert len(state["retrieved_docs"]) == 2
        assert state["retrieval_scores"] == [0.9, 0.85]

    def test_set_response(self):
        """测试设置响应"""
        state = create_initial_state("你好", "session-1")
        set_response(
            state,
            response="你好！我是健身助手。",
            sources=[{"title": "问候语", "url": "https://example.com"}],
        )

        assert state["response"] == "你好！我是健身助手。"
        assert len(state["sources"]) == 1


class TestQueryState:
    """状态查询测试"""

    def test_get_intent(self):
        """测试获取意图"""
        state = create_initial_state("test", "session-1")
        assert get_intent(state) is None

        update_state_intent(state, "chitchat", 0.8)
        assert get_intent(state) == "chitchat"

    def test_get_route(self):
        """测试获取路由"""
        state = create_initial_state("test", "session-1")
        assert get_route(state) is None

        update_state_route(state, "tool")
        assert get_route(state) == "tool"

    def test_has_errors(self):
        """测试检查错误"""
        state = create_initial_state("test", "session-1")
        assert has_errors(state) is False

        update_state_error(state, "error")
        assert has_errors(state) is True

    def test_get_errors(self):
        """测试获取错误列表"""
        state = create_initial_state("test", "session-1")
        assert get_errors(state) == []

        update_state_error(state, "error1")
        update_state_error(state, "error2")
        assert get_errors(state) == ["error1", "error2"]

    def test_get_tool_results(self):
        """测试获取工具结果"""
        state = create_initial_state("test", "session-1")
        assert get_tool_results(state) == []

        add_tool_call(state, "tool1", {}, {"result": 1})
        assert len(get_tool_results(state)) == 1

    def test_get_mcp_results(self):
        """测试获取 MCP 结果"""
        state = create_initial_state("test", "session-1")
        assert get_mcp_results(state) == []

        add_mcp_call(state, "service1", "tool1", {}, {"result": 1})
        assert len(get_mcp_results(state)) == 1

    def test_get_retrieved_docs(self):
        """测试获取检索文档"""
        state = create_initial_state("test", "session-1")
        assert get_retrieved_docs(state) == []

        add_retrieved_docs(state, [{"content": "doc1"}])
        assert len(get_retrieved_docs(state)) == 1

    def test_get_response(self):
        """测试获取响应"""
        state = create_initial_state("test", "session-1")
        assert get_response(state) is None

        set_response(state, "response")
        assert get_response(state) == "response"

    def test_get_messages(self):
        """测试获取消息"""
        state = create_initial_state("test", "session-1")
        assert get_messages(state) == []

    def test_get_user_id(self):
        """测试获取用户 ID"""
        state = create_initial_state("test", "session-1")
        assert get_user_id(state) is None

        state = create_initial_state("test", "session-1", user_id="user-001")
        assert get_user_id(state) == "user-001"

    def test_get_session_id(self):
        """测试获取会话 ID"""
        state = create_initial_state("test", "session-123")
        assert get_session_id(state) == "session-123"


class TestStateToDict:
    """状态序列化测试"""

    def test_state_to_dict(self):
        """测试状态转字典"""
        state = create_initial_state("test", "session-1", user_id="user-001")
        update_state_intent(state, "chitchat", 0.9)

        result = state_to_dict(state)

        assert result["query"] == "test"
        assert result["session_id"] == "session-1"
        assert result["user_id"] == "user-001"
        assert result["intent"] == "chitchat"

    def test_state_to_dict_with_long_messages(self):
        """测试长消息列表的处理"""
        state = create_initial_state("test", "session-1")
        state["messages"] = [{"role": "user", "content": f"msg{i}"} for i in range(10)]

        result = state_to_dict(state)

        assert "messages" in result
        assert "[10 messages]" in result["messages"]
