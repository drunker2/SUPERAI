"""
LLM 模块单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from app.llm import (
    QwenLLM,
    LLMResponse,
    LLMStreamChunk,
    QwenAPIError,
    QwenAuthenticationError,
    QwenRateLimitError,
)
from app.llm.cache import LRUCache, get_llm_cache, clear_llm_cache


# ==================== 缓存测试 ====================


class TestLRUCache:
    """LRU 缓存测试"""

    def test_set_and_get(self):
        """测试基本的存取操作"""
        cache = LRUCache(max_size=10, ttl_seconds=60)

        cache.set("test prompt", {"content": "test response"})

        result = cache.get("test prompt")
        assert result is not None
        assert result["content"] == "test response"

    def test_get_not_exist(self):
        """测试获取不存在的缓存"""
        cache = LRUCache()
        result = cache.get("not exist")
        assert result is None

    def test_cache_expiry(self):
        """测试缓存过期"""
        cache = LRUCache(max_size=10, ttl_seconds=0)  # 立即过期

        cache.set("test", {"content": "test"})

        # 等待过期
        import time
        time.sleep(0.1)

        result = cache.get("test")
        assert result is None

    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应该淘汰 a

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = LRUCache()

        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()

        assert cache.size() == 0

    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LRUCache(max_size=10, ttl_seconds=60)

        cache.set("a", 1)
        cache.set("b", 2)

        stats = cache.stats()
        assert stats["total_size"] == 2
        assert stats["valid_size"] == 2
        assert stats["max_size"] == 10

    def test_global_cache(self):
        """测试全局缓存实例"""
        clear_llm_cache()
        cache = get_llm_cache()

        cache.set("global test", {"data": "test"})
        result = cache.get("global test")
        assert result is not None

        clear_llm_cache()
        result = cache.get("global test")
        assert result is None


# ==================== QwenLLM 测试 ====================


class TestQwenLLM:
    """QwenLLM 测试"""

    def test_init_default_params(self):
        """测试默认参数初始化"""
        llm = QwenLLM()

        assert llm.model == "qwen-max"
        assert llm.temperature == 0.7
        assert llm.max_tokens == 2000
        assert llm.timeout == 30
        assert llm.max_retries == 3

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        llm = QwenLLM(
            model="qwen-plus",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
            max_retries=5,
        )

        assert llm.model == "qwen-plus"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 1000
        assert llm.timeout == 60
        assert llm.max_retries == 5

    def test_build_request_params(self):
        """测试请求参数构建"""
        llm = QwenLLM()

        params = llm._build_request_params("你好", model="qwen-plus", temperature=0.5)

        assert params["model"] == "qwen-plus"
        assert params["temperature"] == 0.5
        assert params["messages"][0]["role"] == "user"
        assert params["messages"][0]["content"] == "你好"

    def test_build_request_params_with_system(self):
        """测试带系统提示词的参数构建"""
        llm = QwenLLM()

        params = llm._build_request_params(
            "你好",
            system_prompt="你是一个健身助手",
        )

        assert len(params["messages"]) == 2
        assert params["messages"][0]["role"] == "system"
        assert params["messages"][0]["content"] == "你是一个健身助手"
        assert params["messages"][1]["role"] == "user"

    def test_build_request_params_with_history(self):
        """测试带历史消息的参数构建"""
        llm = QwenLLM()

        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
        ]

        params = llm._build_request_params("我想健身", history=history)

        assert len(params["messages"]) == 3  # history + current

    def test_repr(self):
        """测试字符串表示"""
        llm = QwenLLM(model="qwen-max", temperature=0.7)
        repr_str = repr(llm)

        assert "QwenLLM" in repr_str
        assert "qwen-max" in repr_str


class TestQwenLLMIntegration:
    """QwenLLM 集成测试 (需要真实 API Key)"""

    @pytest.fixture
    def llm(self):
        """创建 LLM 实例"""
        return QwenLLM()

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    def test_invoke_real_api(self, llm):
        """测试真实 API 调用"""
        response = llm.invoke("你好")

        assert isinstance(response, LLMResponse)
        assert response.content
        assert response.model
        assert response.usage.get("total_tokens", 0) > 0

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    def test_ainvoke_real_api(self, llm):
        """测试异步 API 调用"""
        response = asyncio.run(llm.ainvoke("你好"))

        assert isinstance(response, LLMResponse)
        assert response.content

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    def test_stream_real_api(self, llm):
        """测试流式 API 调用"""
        chunks = list(llm.stream("你好"))

        assert len(chunks) > 0
        assert all(isinstance(chunk, LLMStreamChunk) for chunk in chunks)

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    def test_invalid_api_key(self):
        """测试无效 API Key"""
        llm = QwenLLM(api_key="invalid_key")

        with pytest.raises(QwenAuthenticationError):
            llm.invoke("你好")
