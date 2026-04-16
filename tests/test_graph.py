"""
LangGraph 状态机图测试
"""

import pytest

from app.agent import (
    graph,
    create_agent_graph,
    compile_agent_graph,
    get_graph_mermaid,
    run_agent,
    run_agent_sync,
    create_initial_state,
)


class TestCreateAgentGraph:
    """创建图测试"""

    def test_create_graph(self):
        """测试创建状态机图"""
        workflow = create_agent_graph()

        assert workflow is not None

    def test_compile_graph(self):
        """测试编译图"""
        app = compile_agent_graph()

        assert app is not None

    def test_graph_nodes(self):
        """测试图节点列表"""
        workflow = create_agent_graph()

        # 获取节点
        nodes = workflow.nodes

        # 验证所有必需的节点
        required_nodes = ["intent", "router", "retriever", "tool_executor", "mcp_executor", "generator"]
        for node in required_nodes:
            assert node in nodes, f"Missing node: {node}"


class TestGraphMermaid:
    """图可视化测试"""

    def test_get_graph_mermaid(self):
        """测试获取 Mermaid 格式"""
        mermaid = get_graph_mermaid()

        assert mermaid is not None
        assert len(mermaid) > 0
        # 检查包含关键节点
        assert "intent" in mermaid
        assert "router" in mermaid
        assert "generator" in mermaid

    def test_mermaid_structure(self):
        """测试 Mermaid 结构完整性"""
        mermaid = get_graph_mermaid()

        # 检查包含所有节点
        required_nodes = ["intent", "router", "retriever", "tool_executor", "mcp_executor", "generator"]
        for node in required_nodes:
            assert node in mermaid, f"Mermaid missing node: {node}"


class TestRunAgent:
    """执行图测试"""

    @pytest.mark.asyncio
    async def test_run_agent_chitchat(self):
        """测试闲聊路径"""
        result = await run_agent(
            query="你好",
            session_id="test-session-1",
        )

        assert result is not None
        assert "response" in result
        assert len(result["response"]) > 0
        assert result["intent"] == "chitchat"
        assert result["route"] == "chat"

    @pytest.mark.asyncio
    async def test_run_agent_fitness_consult(self):
        """测试健身咨询路径"""
        result = await run_agent(
            query="怎么练腹肌",
            session_id="test-session-2",
        )

        assert result is not None
        assert "response" in result
        assert result["intent"] == "fitness_consult"
        assert result["route"] == "knowledge"

    @pytest.mark.asyncio
    async def test_run_agent_plan_request(self):
        """测试训练计划请求路径"""
        result = await run_agent(
            query="帮我制定减脂计划",
            session_id="test-session-3",
        )

        assert result is not None
        assert "response" in result
        assert result["intent"] == "plan_request"
        assert result["route"] == "tool"

    def test_run_agent_sync(self):
        """测试同步执行"""
        result = run_agent_sync(
            query="你好",
            session_id="test-session-4",
        )

        assert result is not None
        assert "response" in result


class TestStatePersistence:
    """状态持久化测试"""

    @pytest.mark.asyncio
    async def test_same_session_state(self):
        """测试同一 session 状态保留"""
        session_id = "test-persistence-1"

        # 第一次调用
        result1 = await run_agent(
            query="我叫张三",
            session_id=session_id,
        )

        # 第二次调用（同一 session）
        result2 = await run_agent(
            query="我叫什么名字",
            session_id=session_id,
        )

        # 两次调用应该都有响应
        assert "response" in result1
        assert "response" in result2


class TestGraphExecution:
    """图执行测试"""

    @pytest.mark.asyncio
    async def test_graph_invoke_directly(self):
        """测试直接调用 graph.invoke"""
        state = create_initial_state("你好", "test-direct")
        config = {"configurable": {"thread_id": "test-direct"}}

        result = await graph.ainvoke(state, config)

        assert "response" in result
        assert result["intent"] == "chitchat"

    @pytest.mark.asyncio
    async def test_all_routes(self):
        """测试所有路由路径"""
        test_cases = [
            ("怎么练腹肌", "knowledge"),      # fitness_consult
            ("帮我制定计划", "tool"),         # plan_request
            ("深蹲怎么做", "mcp"),            # exercise_guide (MCP 暂时占位)
            ("你好", "chat"),                 # chitchat
        ]

        for query, expected_route in test_cases:
            result = await run_agent(
                query=query,
                session_id=f"test-route-{query}",
            )

            assert result["route"] == expected_route, f"Query: {query}, Expected: {expected_route}, Got: {result['route']}"
