"""
LLM 响应缓存

使用 Redis 缓存 LLM 响应，减少重复调用
"""

import hashlib
import json
import time
from typing import Any

import redis

from app.config import settings
from app.utils import get_logger
from app.utils.metrics import record_redis_operation

logger = get_logger(__name__)


class LLMResponseCache:
    """
    LLM 响应缓存

    Features:
    - 基于查询内容哈希的缓存键
    - 可配置的 TTL
    - 自动序列化/反序列化
    - 缓存命中率统计
    """

    def __init__(
        self,
        redis_url: str | None = None,
        ttl: int = 3600,  # 默认 1 小时
        key_prefix: str = "llm_cache:",
    ):
        """
        初始化缓存

        Args:
            redis_url: Redis 连接地址
            ttl: 缓存过期时间（秒）
            key_prefix: 缓存键前缀
        """
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl
        self.key_prefix = key_prefix
        self._redis: redis.Redis | None = None

        # 统计
        self._hits = 0
        self._misses = 0

    @property
    def redis_client(self) -> redis.Redis:
        """获取 Redis 客户端（懒加载）"""
        if self._redis is None:
            pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=5,
            )
            self._redis = redis.Redis(connection_pool=pool)
        return self._redis

    def _generate_cache_key(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """
        生成缓存键

        Args:
            prompt: 输入提示词
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            缓存键
        """
        # 构建缓存键内容
        cache_content = {
            "prompt": prompt,
            "model": model or settings.llm_model_name,
            "temperature": temperature or settings.llm_temperature,
        }

        # 添加其他影响结果的参数
        for key, value in sorted(kwargs.items()):
            if key in ("system_prompt", "history"):
                # 对于 history，只取最近几条的消息摘要
                if key == "history" and isinstance(value, list):
                    cache_content[key] = len(value)
                else:
                    cache_content[key] = str(value)[:100]

        # 计算哈希
        content_str = json.dumps(cache_content, sort_keys=True)
        hash_value = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        return f"{self.key_prefix}{hash_value}"

    def get(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> dict | None:
        """
        获取缓存的响应

        Args:
            prompt: 输入提示词
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            缓存的响应或 None
        """
        cache_key = self._generate_cache_key(prompt, model, temperature, **kwargs)

        start = time.perf_counter()
        try:
            cached = self.redis_client.get(cache_key)
            latency = time.perf_counter() - start

            record_redis_operation(operation="get", latency_seconds=latency)

            if cached:
                self._hits += 1
                logger.debug(
                    "缓存命中",
                    cache_key=cache_key,
                    hit_rate=self.hit_rate,
                )
                return json.loads(cached)

            self._misses += 1
            logger.debug("缓存未命中", cache_key=cache_key)
            return None

        except redis.RedisError as e:
            logger.error("缓存读取失败", error=str(e))
            return None

    def set(
        self,
        prompt: str,
        response: dict,
        model: str | None = None,
        temperature: float | None = None,
        ttl: int | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        设置缓存

        Args:
            prompt: 输入提示词
            response: LLM 响应
            model: 模型名称
            temperature: 温度参数
            ttl: 过期时间
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        cache_key = self._generate_cache_key(prompt, model, temperature, **kwargs)

        start = time.perf_counter()
        try:
            self.redis_client.setex(
                cache_key,
                ttl or self.ttl,
                json.dumps(response, ensure_ascii=False),
            )

            latency = time.perf_counter() - start
            record_redis_operation(operation="set", latency_seconds=latency)

            logger.debug(
                "响应已缓存",
                cache_key=cache_key,
                ttl=ttl or self.ttl,
            )
            return True

        except redis.RedisError as e:
            logger.error("缓存写入失败", error=str(e))
            return False

    def delete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        删除缓存

        Args:
            prompt: 输入提示词
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        cache_key = self._generate_cache_key(prompt, model, temperature, **kwargs)

        try:
            self.redis_client.delete(cache_key)
            logger.debug("缓存已删除", cache_key=cache_key)
            return True
        except redis.RedisError as e:
            logger.error("缓存删除失败", error=str(e))
            return False

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            删除的键数量
        """
        try:
            keys = self.redis_client.keys(f"{self.key_prefix}*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info("缓存已清空", deleted_count=deleted)
                return deleted
            return 0
        except redis.RedisError as e:
            logger.error("清空缓存失败", error=str(e))
            return 0

    @property
    def hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
        }


# 全局缓存实例
_cache: LLMResponseCache | None = None


def get_llm_cache() -> LLMResponseCache:
    """获取 LLM 缓存单例"""
    global _cache
    if _cache is None:
        _cache = LLMResponseCache()
    return _cache
