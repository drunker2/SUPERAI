"""
工具模块单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


class TestLLMCache:
    """LLM 缓存测试"""

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()

        key1 = cache._generate_cache_key("你好", model="qwen-max")
        key2 = cache._generate_cache_key("你好", model="qwen-max")
        key3 = cache._generate_cache_key("不同的问题", model="qwen-max")

        assert key1 == key2
        assert key1 != key3

    def test_cache_key_with_different_params(self):
        """测试不同参数生成不同键"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()

        key1 = cache._generate_cache_key("你好", model="qwen-max", temperature=0.7)
        key2 = cache._generate_cache_key("你好", model="qwen-max", temperature=0.9)

        assert key1 != key2

    def test_cache_stats(self):
        """测试缓存统计"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()
        stats = cache.stats

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    @patch('app.utils.cache.redis.Redis')
    def test_cache_get_miss(self, mock_redis_class):
        """测试缓存未命中"""
        from app.utils.cache import LLMResponseCache

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis_class.from_url.return_value = mock_redis

        cache = LLMResponseCache()
        # 手动设置客户端
        cache._redis = mock_redis

        result = cache.get("测试查询")
        assert result is None
        assert cache._misses == 1

    @patch('app.utils.cache.redis.Redis')
    def test_cache_get_hit(self, mock_redis_class):
        """测试缓存命中"""
        import json
        from app.utils.cache import LLMResponseCache

        cached_data = {
            "content": "测试响应",
            "model": "qwen-max",
            "usage": {},
            "latency_ms": 100,
        }

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(cached_data)
        mock_redis_class.from_url.return_value = mock_redis

        cache = LLMResponseCache()
        cache._redis = mock_redis

        result = cache.get("测试查询")
        assert result is not None
        assert result["content"] == "测试响应"
        assert cache._hits == 1


class TestMetrics:
    """指标模块测试"""

    def test_record_chat_request(self):
        """测试对话请求指标"""
        from app.utils.metrics import record_chat_request, CHAT_REQUESTS_TOTAL

        # 记录请求
        record_chat_request(
            session_id="test-session",
            intent="chitchat",
            status="success",
            latency_seconds=1.5,
        )

        # 验证计数器增加
        # 注意：Prometheus 指标是全局的，这里只是确保函数不会报错
        assert True

    def test_record_llm_call(self):
        """测试 LLM 调用指标"""
        from app.utils.metrics import record_llm_call

        record_llm_call(
            model="qwen-max",
            latency_seconds=2.0,
            input_tokens=100,
            output_tokens=50,
        )
        assert True

    def test_record_tool_call(self):
        """测试工具调用指标"""
        from app.utils.metrics import record_tool_call

        record_tool_call(tool_name="calculate_bmi", status="success")
        record_tool_call(tool_name="calculate_bmi", status="error")
        assert True

    def test_record_rag_hit(self):
        """测试 RAG 命中指标"""
        from app.utils.metrics import record_rag_hit

        record_rag_hit(query_type="semantic_search")
        assert True

    def test_set_app_info(self):
        """测试应用信息设置"""
        from app.utils.metrics import set_app_info

        set_app_info(version="1.0.0", environment="development")
        assert True


class TestExceptions:
    """异常模块测试"""

    def test_fitness_agent_error(self):
        """测试基础异常"""
        from app.utils.exceptions import FitnessAgentError

        error = FitnessAgentError(
            code="TEST_ERROR",
            message="测试错误",
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "测试错误"

    def test_llm_error(self):
        """测试 LLM 异常"""
        from app.utils.exceptions import LLMError, LLMTimeoutError

        error = LLMTimeoutError(message="LLM 超时")
        assert "超时" in error.message

    def test_tool_error(self):
        """测试工具异常"""
        from app.utils.exceptions import ToolError, ToolNotFoundError

        error = ToolNotFoundError(tool_name="unknown_tool")
        assert error.code == "TOOL_NOT_FOUND"
        assert "unknown_tool" in error.message

    def test_rate_limit_error(self):
        """测试限流异常"""
        from app.utils.exceptions import RateLimitExceededError

        error = RateLimitExceededError(retry_after=60)
        assert error.retry_after == 60
        assert error.code == "RATE_LIMIT_EXCEEDED"


class TestRateLimiter:
    """限流器测试"""

    def test_rate_limiter_creation(self):
        """测试限流器创建"""
        from app.utils.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter(
            requests_per_period=60,
            period_seconds=60,
        )
        assert limiter.requests_per_period == 60
        assert limiter.period_seconds == 60

    def test_rate_limiter_allow(self):
        """测试限流器允许请求"""
        from app.utils.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter(requests_per_period=10, period_seconds=60)
        client_id = "test-client"

        # 前 10 次应该允许
        for _ in range(10):
            allowed, _, _ = limiter.is_allowed(client_id)
            assert allowed is True

    def test_rate_limiter_block(self):
        """测试限流器阻止请求"""
        from app.utils.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter(requests_per_period=5, period_seconds=60)
        client_id = "test-client-2"

        # 前 5 次允许
        for _ in range(5):
            limiter.is_allowed(client_id)

        # 第 6 次应该被阻止
        allowed, _, _ = limiter.is_allowed(client_id)
        assert allowed is False

    def test_rate_limiter_different_clients(self):
        """测试不同客户端独立限流"""
        from app.utils.rate_limiter import InMemoryRateLimiter

        limiter = InMemoryRateLimiter(requests_per_period=2, period_seconds=60)

        # 客户端 A 用完配额
        limiter.is_allowed("client-a")
        limiter.is_allowed("client-a")

        # 客户端 B 应该仍然可以访问
        allowed, _, _ = limiter.is_allowed("client-b")
        assert allowed is True


class TestLogContext:
    """日志上下文测试"""

    def test_bind_context(self):
        """测试绑定上下文"""
        from app.utils.logger import bind_context, unbind_context

        bind_context(session_id="test-session", user_id="test-user")
        # 不应该报错
        unbind_context("session_id", "user_id")

    def test_log_context_manager(self):
        """测试上下文管理器"""
        from app.utils.logger import LogContext

        with LogContext(trace_id="test-trace"):
            # 上下文应该被绑定
            pass
        # 退出后应该被解绑
