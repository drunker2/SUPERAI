"""
端到端测试
测试完整的用户场景
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio


class TestE2EChatFlow:
    """端到端对话流程测试"""

    @pytest.fixture
    def mock_llm_response(self):
        """模拟 LLM 响应"""
        return MagicMock(
            content="你好！我是你的健身助手。",
            model="qwen-max",
            usage={"input_tokens": 5, "output_tokens": 10},
            latency_ms=500,
        )

    def test_agent_state_flow(self):
        """测试 Agent 状态流程"""
        from app.agent.state import create_initial_state

        state = create_initial_state(
            query="你好",
            session_id="test-session",
        )

        assert state["query"] == "你好"
        assert state["session_id"] == "test-session"

    def test_fitness_consult_flow(self):
        """测试健身咨询流程"""
        from app.agent.state import create_initial_state

        state = create_initial_state(
            query="怎么增肌最快？",
            session_id="test-session",
        )

        assert "增肌" in state["query"]

    @pytest.mark.asyncio
    async def test_bmi_calculation_flow(self):
        """测试 BMI 计算流程"""
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


class TestE2EToolFlow:
    """端到端工具流程测试"""

    @pytest.mark.asyncio
    async def test_bmi_tool_e2e(self):
        """测试 BMI 工具端到端"""
        from app.tools.fitness import CalculateBMITool

        tool = CalculateBMITool()

        result = await tool.execute(weight=70, height=175)

        assert result.is_success
        assert "bmi" in result.data
        assert 22 < result.data["bmi"] < 23

    @pytest.mark.asyncio
    async def test_bmr_tool_e2e(self):
        """测试 BMR 工具端到端"""
        from app.tools.fitness import CalculateBMRTool

        tool = CalculateBMRTool()

        result = await tool.execute(
            weight=70,
            height=175,
            age=25,
            gender="male",
        )

        assert result.is_success
        assert "bmr" in result.data

    @pytest.mark.asyncio
    async def test_body_fat_tool_e2e(self):
        """测试体脂率工具端到端"""
        from app.tools.fitness import CalculateBodyFatTool

        tool = CalculateBodyFatTool()

        result = await tool.execute(
            waist=80,
            neck=35,
            height=175,
            gender="male",
        )

        assert result.is_success
        assert "body_fat_percent" in result.data


class TestE2EAuthentication:
    """端到端认证测试"""

    def test_password_flow(self):
        """测试密码流程"""
        from app.auth.service import AuthService

        service = AuthService()

        # 创建密码
        password = "test_password_123"
        hashed = service.get_password_hash(password)

        # 验证密码
        assert service.verify_password(password, hashed) is True
        assert service.verify_password("wrong_password", hashed) is False

    def test_token_flow(self):
        """测试 Token 流程"""
        from app.auth.service import AuthService

        service = AuthService()

        # 创建 Token
        token = service.create_access_token(
            data={"sub": "1", "username": "testuser"}
        )

        # 验证 Token
        token_data = service.decode_token(token)

        assert token_data is not None
        assert token_data.user_id == 1
        assert token_data.username == "testuser"


class TestE2ESession:
    """端到端会话测试"""

    @patch('app.agent.memory.redis_memory.redis.ConnectionPool.from_url')
    def test_session_lifecycle(self, mock_pool_from_url):
        """测试会话生命周期"""
        import json

        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0

        with patch('app.agent.memory.redis_memory.redis.Redis') as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            from app.agent.memory.redis_memory import RedisChatMessageHistory
            from langchain_core.messages import HumanMessage, AIMessage

            # 创建会话
            history = RedisChatMessageHistory("test-session-e2e")

            # 添加用户消息
            history.add_message(HumanMessage(content="你好"))

            # 添加 AI 响应
            history.add_message(AIMessage(content="你好！有什么可以帮助你的？"))

            # 验证 rpush 被调用
            assert mock_redis.rpush.called


class TestE2EMetrics:
    """端到端指标测试"""

    def test_metrics_recording(self):
        """测试指标记录"""
        from app.utils.metrics import (
            record_chat_request,
            record_tool_call,
            record_llm_call,
        )

        # 记录各种指标
        record_chat_request(
            session_id="test",
            intent="chitchat",
            status="success",
            latency_seconds=1.0,
        )

        record_tool_call(tool_name="calculate_bmi", status="success")

        record_llm_call(
            model="qwen-max",
            latency_seconds=0.5,
            input_tokens=10,
            output_tokens=20,
        )

        # 指标记录不应该报错
        assert True


class TestE2ECache:
    """端到端缓存测试"""

    @patch('app.utils.cache.redis.Redis')
    def test_cache_lifecycle(self, mock_redis_class):
        """测试缓存生命周期"""
        import json

        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis

        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()
        cache._redis = mock_redis

        # 设置缓存
        test_data = {"content": "测试响应", "model": "qwen"}
        cache.set("test_query", test_data)

        # 验证 setex 被调用
        mock_redis.setex.assert_called_once()

        # 模拟获取缓存
        mock_redis.get.return_value = json.dumps(test_data)
        result = cache.get("test_query")

        assert result is not None
        assert result["content"] == "测试响应"
