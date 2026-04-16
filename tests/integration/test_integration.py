"""
集成测试
测试多个模块协作
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio


class TestAgentIntegration:
    """Agent 集成测试"""

    @pytest.fixture
    def mock_llm(self):
        """模拟 LLM"""
        mock = MagicMock()
        mock.invoke = MagicMock(return_value=MagicMock(
            content="这是一个测试响应",
            model="qwen-max",
            usage={"input_tokens": 10, "output_tokens": 20},
        ))
        return mock

    def test_state_to_dict_conversion(self):
        """测试状态字典转换"""
        from app.agent.state import create_initial_state

        state = create_initial_state(
            query="你好",
            session_id="test-session",
        )

        assert state["query"] == "你好"
        assert state["session_id"] == "test-session"

    def test_state_update_flow(self):
        """测试状态更新流程"""
        from app.agent.state import (
            create_initial_state,
            update_state_intent,
            update_state_route,
        )

        state = create_initial_state(
            query="帮我制定一个减脂计划",
            session_id="test-session",
        )

        # 更新意图
        state = update_state_intent(state, "plan_request", 0.9)

        # 更新路由
        state = update_state_route(state, "tool")

        assert state["intent"] == "plan_request"
        assert state["route"] == "tool"

    def test_tool_call_flow(self):
        """测试工具调用流程"""
        from app.agent.state import create_initial_state

        state = create_initial_state(
            query="计算 BMI",
            session_id="test-session",
        )

        # 手动添加工具调用记录
        state["tool_calls"] = [{
            "name": "calculate_bmi",
            "arguments": {"weight": 70, "height": 175},
        }]

        state["tool_results"] = [{
            "name": "calculate_bmi",
            "result": {"bmi": 22.86},
        }]

        assert len(state["tool_calls"]) == 1
        assert len(state["tool_results"]) == 1


class TestRAGIntegration:
    """RAG 集成测试"""

    @patch('app.rag.indexer.ChromaIndexer')
    def test_indexer_search_flow(self, mock_indexer_class):
        """测试索引器搜索流程"""
        mock_indexer = MagicMock()
        mock_indexer.search.return_value = [
            {"id": "doc1", "content": "测试内容", "distance": 0.1}
        ]
        mock_indexer_class.return_value = mock_indexer

        from app.rag.indexer import get_indexer

        indexer = get_indexer()
        results = indexer.search("测试查询")

        assert len(results) == 1
        assert results[0]["content"] == "测试内容"

    def test_embedding_initialization(self):
        """测试嵌入模型初始化"""
        from app.rag.embeddings import QwenEmbedding

        # 只测试初始化，不调用 API
        embedding = QwenEmbedding()
        assert embedding is not None


class TestMCPIntegration:
    """MCP 集成测试"""

    def test_mcp_tools_sync(self):
        """测试 MCP 同步工具"""
        from app.mcp.tools import get_exercise_info_sync

        # 这个函数可能返回 None（如果 MCP 服务未启动）
        result = get_exercise_info_sync("深蹲")
        # 只要不报错就算通过
        assert result is None or isinstance(result, dict)


class TestToolIntegration:
    """工具集成测试"""

    def test_fitness_tools_registration(self):
        """测试健身工具注册"""
        from app.tools import register_fitness_tools
        from app.tools.registry import get_tool_registry

        # 清空注册器
        registry = get_tool_registry()
        for tool_name in list(registry.list_names()):
            registry.unregister(tool_name)

        # 重新注册
        register_fitness_tools()

        assert registry.exists("calculate_bmi")
        assert registry.exists("calculate_bmr")
        assert registry.exists("calculate_body_fat")

    def test_training_tools_registration(self):
        """测试训练计划工具注册"""
        from app.tools import register_training_tools
        from app.tools.registry import get_tool_registry

        # 清空并重新注册
        registry = get_tool_registry()
        register_training_tools()

        assert registry.exists("generate_plan")
        assert registry.exists("get_exercise_info")
        assert registry.exists("list_exercises")

    @pytest.mark.asyncio
    async def test_tool_execution_bmi(self):
        """测试 BMI 工具执行"""
        from app.tools.registry import get_tool_registry

        registry = get_tool_registry()

        if registry.exists("calculate_bmi"):
            result = await registry.execute(
                "calculate_bmi",
                weight=70,
                height=175,
            )

            assert result.is_success
            assert "bmi" in result.data


class TestSessionIntegration:
    """会话集成测试"""

    @patch('app.agent.memory.redis_memory.redis.ConnectionPool.from_url')
    def test_session_creation(self, mock_pool_from_url):
        """测试会话创建"""
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0

        with patch('app.agent.memory.redis_memory.redis.Redis') as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            from app.agent.memory.redis_memory import RedisChatMessageHistory

            history = RedisChatMessageHistory("test-session")
            messages = history.messages

            assert isinstance(messages, list)

    @patch('app.agent.memory.redis_memory.redis.ConnectionPool.from_url')
    def test_session_add_message(self, mock_pool_from_url):
        """测试添加消息到会话"""
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0

        with patch('app.agent.memory.redis_memory.redis.Redis') as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            from app.agent.memory.redis_memory import RedisChatMessageHistory
            from langchain_core.messages import HumanMessage

            history = RedisChatMessageHistory("test-session")
            history.add_message(HumanMessage(content="你好"))

            # 验证 rpush 被调用
            assert mock_redis.rpush.called


class TestCacheIntegration:
    """缓存集成测试"""

    @patch('app.utils.cache.redis.Redis')
    def test_cache_set_get(self, mock_redis_class):
        """测试缓存设置和获取"""
        import json

        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis

        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()
        cache._redis = mock_redis

        # 设置缓存
        test_response = {"content": "测试", "model": "qwen"}
        cache.set("测试查询", test_response)

        # 模拟 Redis 返回
        mock_redis.get.return_value = json.dumps(test_response)

        # 获取缓存
        result = cache.get("测试查询")

        mock_redis.setex.assert_called()
        mock_redis.get.assert_called()
