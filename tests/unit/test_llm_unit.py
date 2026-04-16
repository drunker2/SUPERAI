"""
LLM 模块单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


class TestLLMResponse:
    """LLM 响应模型测试"""

    def test_llm_response_creation(self):
        """测试 LLM 响应创建"""
        from app.llm.qwen import LLMResponse

        response = LLMResponse(
            content="你好！",
            model="qwen-max",
            usage={"input_tokens": 10, "output_tokens": 5},
            request_id="test-123",
            latency_ms=100.5,
            finish_reason="stop",
        )

        assert response.content == "你好！"
        assert response.model == "qwen-max"
        assert response.usage["input_tokens"] == 10
        assert response.latency_ms == 100.5

    def test_llm_stream_chunk(self):
        """测试流式响应块"""
        from app.llm.qwen import LLMStreamChunk

        chunk = LLMStreamChunk(
            content="测试",
            finish_reason=None,
        )

        assert chunk.content == "测试"
        assert chunk.finish_reason is None


class TestQwenLLMParams:
    """QwenLLM 参数测试"""

    def test_default_params(self):
        """测试默认参数"""
        from app.llm.qwen import QwenLLM

        llm = QwenLLM()

        # 默认从配置读取
        assert llm.model is not None
        assert llm.temperature > 0
        assert llm.max_tokens > 0

    def test_custom_params(self):
        """测试自定义参数"""
        from app.llm.qwen import QwenLLM

        llm = QwenLLM(
            model="qwen-turbo",
            temperature=0.5,
            max_tokens=100,
        )

        assert llm.model == "qwen-turbo"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 100

    def test_build_request_params(self):
        """测试请求参数构建"""
        from app.llm.qwen import QwenLLM

        llm = QwenLLM()
        params = llm._build_request_params("你好")

        assert "model" in params
        assert "messages" in params
        assert "temperature" in params
        assert len(params["messages"]) == 1
        assert params["messages"][0]["role"] == "user"

    def test_build_request_params_with_system(self):
        """测试带系统提示的参数构建"""
        from app.llm.qwen import QwenLLM

        llm = QwenLLM()
        params = llm._build_request_params(
            "你好",
            system_prompt="你是一个健身助手",
        )

        assert len(params["messages"]) == 2
        assert params["messages"][0]["role"] == "system"

    def test_build_request_params_with_history(self):
        """测试带历史消息的参数构建"""
        from app.llm.qwen import QwenLLM
        from langchain_core.messages import HumanMessage, AIMessage

        llm = QwenLLM()
        history = [
            HumanMessage(content="你好"),
            AIMessage(content="你好！有什么可以帮助你的？"),
        ]

        params = llm._build_request_params("谢谢", history=history)

        # 应该包含历史消息 + 新消息
        assert len(params["messages"]) >= 2


class TestLLMExceptions:
    """LLM 异常测试"""

    def test_error_code_mapping(self):
        """测试错误码映射"""
        from app.llm.qwen import QwenLLM
        from app.llm.exceptions import (
            QwenAuthenticationError,
            QwenRateLimitError,
            QwenContentFilterError,
        )

        llm = QwenLLM()

        # 验证错误码映射存在
        assert "InvalidApiKey" in llm.ERROR_CODE_MAP
        assert "RateLimit" in llm.ERROR_CODE_MAP
        assert "DataInspectionFailed" in llm.ERROR_CODE_MAP

    def test_handle_error_authentication(self):
        """测试认证错误处理"""
        from app.llm.qwen import QwenLLM
        from app.llm.exceptions import QwenAuthenticationError

        llm = QwenLLM()

        with pytest.raises(QwenAuthenticationError):
            llm._handle_error(Exception("InvalidApiKey: invalid api key"))

    def test_handle_error_rate_limit(self):
        """测试限流错误处理"""
        from app.llm.qwen import QwenLLM
        from app.llm.exceptions import QwenRateLimitError

        llm = QwenLLM()

        with pytest.raises(QwenRateLimitError):
            llm._handle_error(Exception("RateLimit: too many requests"))


class TestLLMCache:
    """LLM 缓存集成测试"""

    @patch('app.llm.qwen.Generation.call')
    def test_invoke_with_cache(self, mock_call):
        """测试带缓存的调用"""
        from app.llm.qwen import QwenLLM

        # 模拟 API 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "测试响应"
        mock_response.output.choices[0].finish_reason = "stop"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.request_id = "test-123"

        mock_call.return_value = mock_response

        llm = QwenLLM(use_cache=False)  # 先禁用缓存测试

        response = llm.invoke("测试问题")

        assert response.content == "测试响应"
        assert mock_call.call_count == 1


class TestLLMCacheIntegration:
    """LLM 缓存集成测试"""

    def test_cache_key_consistency(self):
        """测试缓存键一致性"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()

        # 相同输入应该生成相同键
        key1 = cache._generate_cache_key("你好")
        key2 = cache._generate_cache_key("你好")

        assert key1 == key2

    def test_cache_key_different_model(self):
        """测试不同模型生成不同键"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()

        key1 = cache._generate_cache_key("你好", model="qwen-max")
        key2 = cache._generate_cache_key("你好", model="qwen-turbo")

        assert key1 != key2

    def test_cache_key_with_history(self):
        """测试带历史的缓存键"""
        from app.utils.cache import LLMResponseCache

        cache = LLMResponseCache()

        history1 = [{"type": "human", "content": "问题1"}]
        history2 = [{"type": "human", "content": "问题2"}, {"type": "ai", "content": "回答"}]

        key1 = cache._generate_cache_key("你好", history=history1)
        key2 = cache._generate_cache_key("你好", history=history2)

        # 不同历史长度应该生成不同键
        assert key1 != key2
