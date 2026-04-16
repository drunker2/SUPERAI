"""
通义千问 LLM 封装
支持同步/异步调用，带重试和超时控制
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Iterator

import dashscope
from dashscope import Generation
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.llm.exceptions import (
    QwenAPIError,
    QwenAuthenticationError,
    QwenContentFilterError,
    QwenInvalidRequestError,
    QwenModelNotFoundError,
    QwenRateLimitError,
    QwenServiceUnavailableError,
    QwenTimeoutError,
)
from app.utils import get_logger, bind_context
from app.utils.metrics import record_llm_call

logger = get_logger(__name__)


# ==================== 缓存支持 ====================


def _get_cache():
    """懒加载缓存"""
    from app.utils.cache import get_llm_cache
    return get_llm_cache()


# ==================== 响应模型 ====================


class LLMResponse(BaseModel):
    """LLM 响应模型"""

    content: str = Field(..., description="生成的文本内容")
    model: str = Field(..., description="使用的模型名称")
    usage: dict[str, int] = Field(default_factory=dict, description="Token 使用统计")
    request_id: str | None = Field(default=None, description="请求 ID")
    latency_ms: float = Field(default=0, description="响应延迟(毫秒)")
    finish_reason: str | None = Field(default=None, description="结束原因")


class LLMStreamChunk(BaseModel):
    """LLM 流式响应块"""

    content: str = Field(..., description="当前块内容")
    finish_reason: str | None = Field(default=None, description="结束原因")


# ==================== 基类定义 ====================


class BaseLLM(ABC):
    """LLM 基类"""

    @abstractmethod
    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """同步调用"""
        pass

    @abstractmethod
    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """异步调用"""
        pass

    @abstractmethod
    def stream(self, prompt: str, **kwargs: Any) -> Iterator[LLMStreamChunk]:
        """流式调用"""
        pass

    @abstractmethod
    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[LLMStreamChunk]:
        """异步流式调用"""
        pass


# ==================== 通义千问实现 ====================


class QwenLLM(BaseLLM):
    """
    通义千问 LLM 封装

    Features:
    - 同步/异步调用
    - 流式输出
    - 自动重试 (网络错误、限流)
    - 超时控制
    - 调用日志
    - 错误分类
    """

    # 错误码映射
    ERROR_CODE_MAP = {
        "InvalidApiKey": QwenAuthenticationError,
        "InvalidParameter": QwenInvalidRequestError,
        "ModelNotFound": QwenModelNotFoundError,
        "RateLimit": QwenRateLimitError,
        "DataInspectionFailed": QwenContentFilterError,
        "InternalError": QwenServiceUnavailableError,
        "ServiceUnavailable": QwenServiceUnavailableError,
    }

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
        max_retries: int = 3,
        api_key: str | None = None,
        use_cache: bool = True,
    ):
        """
        初始化通义千问 LLM

        Args:
            model: 模型名称，默认使用配置
            temperature: 生成温度
            max_tokens: 最大生成 token 数
            timeout: 超时时间(秒)
            max_retries: 最大重试次数
            api_key: API Key，默认使用配置
            use_cache: 是否启用响应缓存
        """
        self.model = model or settings.llm_model_name
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.timeout = timeout or settings.llm_timeout
        self.max_retries = max_retries
        self.api_key = api_key or settings.dashscope_api_key
        self.use_cache = use_cache

        # 配置 dashscope
        if self.api_key:
            dashscope.api_key = self.api_key

    def _build_request_params(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """构建请求参数"""
        params = {
            "model": kwargs.pop("model", self.model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.pop("temperature", self.temperature),
            "max_tokens": kwargs.pop("max_tokens", self.max_tokens),
            "result_format": "message",
        }

        # 添加系统提示词
        if "system_prompt" in kwargs:
            params["messages"] = [
                {"role": "system", "content": kwargs.pop("system_prompt")},
                params["messages"][0],
            ]

        # 添加历史消息
        if "history" in kwargs:
            history = kwargs.pop("history")
            if history:
                # 插入历史消息到 user 消息之前
                system_msg = params["messages"][0] if len(params["messages"]) > 1 else None
                user_msg = params["messages"][-1]
                params["messages"] = []
                if system_msg:
                    params["messages"].append(system_msg)
                params["messages"].extend(history)
                params["messages"].append(user_msg)

        # 合并其他参数
        params.update(kwargs)

        return params

    def _handle_error(self, error: Exception, request_id: str | None = None) -> None:
        """处理错误，转换为具体异常类型"""
        error_str = str(error).lower()

        # 尝试从错误信息中提取错误码
        for code, exc_class in self.ERROR_CODE_MAP.items():
            if code.lower() in error_str:
                raise exc_class(
                    message=str(error),
                    request_id=request_id,
                )

        # 默认抛出通用异常
        raise QwenAPIError(
            message=str(error),
            request_id=request_id,
        )

    def _log_request(
        self,
        prompt: str,
        response: LLMResponse,
        duration_ms: float,
    ) -> None:
        """记录请求日志"""
        logger.info(
            "LLM 调用完成",
            model=response.model,
            request_id=response.request_id,
            input_tokens=response.usage.get("input_tokens", 0),
            output_tokens=response.usage.get("output_tokens", 0),
            total_tokens=response.usage.get("total_tokens", 0),
            latency_ms=round(response.latency_ms, 2),
            finish_reason=response.finish_reason,
        )

    @retry(
        retry=retry_if_exception_type((QwenRateLimitError, QwenServiceUnavailableError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        同步调用 LLM

        Args:
            prompt: 输入提示词
            **kwargs: 其他参数 (model, temperature, max_tokens, system_prompt, history, use_cache)

        Returns:
            LLMResponse 对象
        """
        use_cache = kwargs.pop("use_cache", self.use_cache)

        # 尝试从缓存获取
        if use_cache:
            try:
                cache = _get_cache()
                cached = cache.get(prompt, **kwargs)
                if cached:
                    logger.info("LLM 响应从缓存返回", cached=True)
                    return LLMResponse(**cached)
            except Exception as e:
                logger.warning("缓存读取失败，继续调用 LLM", error=str(e))

        start_time = time.perf_counter()
        params = self._build_request_params(prompt, **kwargs)

        bind_context(model=params["model"], prompt_length=len(prompt))

        try:
            response = Generation.call(**params)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # 检查响应状态
            if response.status_code != 200:
                self._handle_error(
                    Exception(response.code or response.message),
                    request_id=response.request_id,
                )

            # 提取响应内容
            content = response.output.choices[0].message.content
            finish_reason = response.output.choices[0].finish_reason

            # 构建 LLMResponse
            llm_response = LLMResponse(
                content=content,
                model=params["model"],
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                request_id=response.request_id,
                latency_ms=duration_ms,
                finish_reason=finish_reason,
            )

            self._log_request(prompt, llm_response, duration_ms)

            # 记录 Prometheus 指标
            record_llm_call(
                model=params["model"],
                latency_seconds=duration_ms / 1000,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # 存入缓存
            if use_cache:
                try:
                    cache = _get_cache()
                    cache.set(prompt, llm_response.model_dump(), **kwargs)
                except Exception as e:
                    logger.warning("缓存写入失败", error=str(e))

            return llm_response

        except QwenAPIError:
            raise
        except Exception as e:
            self._handle_error(e)

    @retry(
        retry=retry_if_exception_type((QwenRateLimitError, QwenServiceUnavailableError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def ainvoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        异步调用 LLM

        Args:
            prompt: 输入提示词
            **kwargs: 其他参数

        Returns:
            LLMResponse 对象
        """
        use_cache = kwargs.pop("use_cache", self.use_cache)

        # 尝试从缓存获取
        if use_cache:
            try:
                cache = _get_cache()
                cached = cache.get(prompt, **kwargs)
                if cached:
                    logger.info("LLM 响应从缓存返回", cached=True)
                    return LLMResponse(**cached)
            except Exception as e:
                logger.warning("缓存读取失败，继续调用 LLM", error=str(e))

        start_time = time.perf_counter()
        params = self._build_request_params(prompt, **kwargs)

        bind_context(model=params["model"], prompt_length=len(prompt))

        try:
            # dashscope 异步调用
            response = await asyncio.to_thread(
                Generation.call,
                **params,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # 检查响应状态
            if response.status_code != 200:
                self._handle_error(
                    Exception(response.code or response.message),
                    request_id=response.request_id,
                )

            # 提取响应内容
            content = response.output.choices[0].message.content
            finish_reason = response.output.choices[0].finish_reason

            llm_response = LLMResponse(
                content=content,
                model=params["model"],
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                request_id=response.request_id,
                latency_ms=duration_ms,
                finish_reason=finish_reason,
            )

            self._log_request(prompt, llm_response, duration_ms)

            # 记录 Prometheus 指标
            record_llm_call(
                model=params["model"],
                latency_seconds=duration_ms / 1000,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # 存入缓存
            if use_cache:
                try:
                    cache = _get_cache()
                    cache.set(prompt, llm_response.model_dump(), **kwargs)
                except Exception as e:
                    logger.warning("缓存写入失败", error=str(e))

            return llm_response

        except QwenAPIError:
            raise
        except Exception as e:
            self._handle_error(e)

    def stream(self, prompt: str, **kwargs: Any) -> Iterator[LLMStreamChunk]:
        """
        流式调用 LLM

        Args:
            prompt: 输入提示词
            **kwargs: 其他参数

        Yields:
            LLMStreamChunk 对象
        """
        params = self._build_request_params(prompt, **kwargs)
        params["stream"] = True

        bind_context(model=params["model"], prompt_length=len(prompt), stream=True)

        try:
            responses = Generation.call(**params)

            for response in responses:
                if response.status_code != 200:
                    self._handle_error(
                        Exception(response.code or response.message),
                        request_id=response.request_id,
                    )

                choice = response.output.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

                yield LLMStreamChunk(
                    content=content,
                    finish_reason=finish_reason,
                )

            logger.info("LLM 流式调用完成", model=params["model"])

        except QwenAPIError:
            raise
        except Exception as e:
            self._handle_error(e)

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncIterator[LLMStreamChunk]:
        """
        异步流式调用 LLM

        Args:
            prompt: 输入提示词
            **kwargs: 其他参数

        Yields:
            LLMStreamChunk 对象
        """
        params = self._build_request_params(prompt, **kwargs)
        params["stream"] = True

        bind_context(model=params["model"], prompt_length=len(prompt), stream=True)

        try:
            # 在线程中执行同步流式调用
            def sync_stream():
                return Generation.call(**params)

            responses = await asyncio.to_thread(sync_stream)

            for response in responses:
                if response.status_code != 200:
                    self._handle_error(
                        Exception(response.code or response.message),
                        request_id=response.request_id,
                    )

                choice = response.output.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

                yield LLMStreamChunk(
                    content=content,
                    finish_reason=finish_reason,
                )

            logger.info("LLM 异步流式调用完成", model=params["model"])

        except QwenAPIError:
            raise
        except Exception as e:
            self._handle_error(e)

    def __repr__(self) -> str:
        return f"QwenLLM(model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens})"
