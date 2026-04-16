"""
LLM 响应缓存
简单的内存缓存实现，用于缓存相同问题的响应
"""

import hashlib
import time
from collections import OrderedDict
from threading import Lock
from typing import Any


class LRUCache:
    """线程安全的 LRU 缓存"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        初始化 LRU 缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间(秒)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()

    def _generate_key(self, prompt: str, **kwargs: Any) -> str:
        """生成缓存键"""
        # 对参数进行排序后序列化，确保相同参数生成相同的键
        key_data = {"prompt": prompt, **kwargs}
        key_str = str(sorted(key_data.items()))
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, prompt: str, **kwargs: Any) -> Any | None:
        """
        获取缓存

        Args:
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            缓存的响应，如果不存在或已过期则返回 None
        """
        key = self._generate_key(prompt, **kwargs)

        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # 检查是否过期
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None

            # 移动到末尾 (最近使用)
            self._cache.move_to_end(key)
            return value

    def set(self, prompt: str, value: Any, **kwargs: Any) -> None:
        """
        设置缓存

        Args:
            prompt: 提示词
            value: 缓存值
            **kwargs: 其他参数
        """
        key = self._generate_key(prompt, **kwargs)

        with self._lock:
            # 如果已存在，更新并移动到末尾
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, time.time())
                return

            # 检查是否需要淘汰
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (value, time.time())

    def delete(self, prompt: str, **kwargs: Any) -> bool:
        """
        删除缓存

        Args:
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            是否成功删除
        """
        key = self._generate_key(prompt, **kwargs)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            current_time = time.time()
            valid_count = sum(
                1 for _, timestamp in self._cache.values()
                if current_time - timestamp <= self.ttl_seconds
            )
            return {
                "total_size": len(self._cache),
                "valid_size": valid_count,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
            }


# 全局缓存实例
_llm_cache: LRUCache | None = None


def get_llm_cache() -> LRUCache:
    """获取 LLM 缓存实例"""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LRUCache()
    return _llm_cache


def clear_llm_cache() -> None:
    """清空 LLM 缓存"""
    global _llm_cache
    if _llm_cache is not None:
        _llm_cache.clear()
