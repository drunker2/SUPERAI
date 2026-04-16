"""
Redis 会话记忆管理
替代内存会话管理，支持持久化和分布式部署
"""

import json
import time
from typing import Any

import redis
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)


class RedisChatMessageHistory(BaseChatMessageHistory):
    """
    基于 Redis 的会话记忆

    Features:
    - 消息持久化存储
    - TTL 自动过期
    - 连接池复用
    - 线程安全
    """

    def __init__(
        self,
        session_id: str,
        redis_url: str | None = None,
        ttl: int | None = None,
        key_prefix: str = "chat_history:",
    ):
        """
        初始化 Redis 会话记忆

        Args:
            session_id: 会话 ID
            redis_url: Redis 连接地址，默认使用配置
            ttl: 过期时间(秒)，默认 7 天
            key_prefix: Redis key 前缀
        """
        self.session_id = session_id
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl or settings.redis_session_ttl
        self.key_prefix = key_prefix
        self.key = f"{key_prefix}{session_id}"

        # 创建 Redis 连接池
        self._redis: redis.Redis | None = None

    @property
    def redis_client(self) -> redis.Redis:
        """获取 Redis 客户端（懒加载）"""
        if self._redis is None:
            pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=10,
            )
            self._redis = redis.Redis(connection_pool=pool)
        return self._redis

    @property
    def messages(self) -> list[BaseMessage]:
        """获取所有消息"""
        try:
            items = self.redis_client.lrange(self.key, 0, -1)
            if not items:
                return []
            messages = messages_from_dict(
                [json.loads(item) for item in items]
            )
            return messages
        except redis.RedisError as e:
            logger.error(f"Redis 读取消息失败: {e}", session_id=self.session_id)
            return []

    def add_message(self, message: BaseMessage) -> None:
        """添加消息"""
        try:
            message_dict = messages_to_dict([message])[0]
            self.redis_client.rpush(self.key, json.dumps(message_dict, ensure_ascii=False))
            # 刷新过期时间
            self.redis_client.expire(self.key, self.ttl)
            logger.debug(
                "消息已保存到 Redis",
                session_id=self.session_id,
                message_type=message.type,
            )
        except redis.RedisError as e:
            logger.error(f"Redis 保存消息失败: {e}", session_id=self.session_id)

    def clear(self) -> None:
        """清空会话"""
        try:
            self.redis_client.delete(self.key)
            logger.info("会话已清空", session_id=self.session_id)
        except redis.RedisError as e:
            logger.error(f"Redis 清空会话失败: {e}", session_id=self.session_id)

    def get_recent_messages(self, n: int = 10) -> list[BaseMessage]:
        """
        获取最近 N 条消息

        Args:
            n: 消息数量

        Returns:
            消息列表
        """
        try:
            items = self.redis_client.lrange(self.key, -n, -1)
            if not items:
                return []
            messages = messages_from_dict(
                [json.loads(item) for item in items]
            )
            return messages
        except redis.RedisError as e:
            logger.error(f"Redis 读取消息失败: {e}", session_id=self.session_id)
            return []

    def get_message_count(self) -> int:
        """获取消息数量"""
        try:
            return self.redis_client.llen(self.key)
        except redis.RedisError:
            return 0

    def set_ttl(self, ttl: int) -> None:
        """
        设置过期时间

        Args:
            ttl: 过期时间(秒)
        """
        try:
            self.redis_client.expire(self.key, ttl)
            logger.debug("TTL 已更新", session_id=self.session_id, ttl=ttl)
        except redis.RedisError as e:
            logger.error(f"Redis 设置 TTL 失败: {e}", session_id=self.session_id)

    def get_ttl(self) -> int:
        """获取剩余过期时间"""
        try:
            return self.redis_client.ttl(self.key)
        except redis.RedisError:
            return -1


class RedisSessionManager:
    """
    Redis 会话管理器

    管理多个会话的生命周期
    """

    def __init__(
        self,
        redis_url: str | None = None,
        ttl: int | None = None,
    ):
        """
        初始化会话管理器

        Args:
            redis_url: Redis 连接地址
            ttl: 会话过期时间
        """
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl or settings.redis_session_ttl
        self._pool: redis.ConnectionPool | None = None

    @property
    def redis_client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
            )
        return redis.Redis(connection_pool=self._pool)

    def get_session(self, session_id: str) -> RedisChatMessageHistory:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话历史对象
        """
        return RedisChatMessageHistory(
            session_id=session_id,
            redis_url=self.redis_url,
            ttl=self.ttl,
        )

    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话 ID

        Returns:
            是否存在
        """
        try:
            key = f"chat_history:{session_id}"
            return self.redis_client.exists(key) > 0
        except redis.RedisError:
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            key = f"chat_history:{session_id}"
            self.redis_client.delete(key)
            logger.info("会话已删除", session_id=session_id)
            return True
        except redis.RedisError as e:
            logger.error(f"删除会话失败: {e}", session_id=session_id)
            return False

    def clear_session(self, session_id: str) -> bool:
        """
        清空会话内容

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        return self.delete_session(session_id)

    def get_all_session_ids(self, pattern: str = "chat_history:*") -> list[str]:
        """
        获取所有会话 ID

        Args:
            pattern: Key 匹配模式

        Returns:
            会话 ID 列表
        """
        try:
            keys = self.redis_client.keys(pattern)
            prefix = "chat_history:"
            return [key.replace(prefix, "") for key in keys]
        except redis.RedisError as e:
            logger.error(f"获取会话列表失败: {e}")
            return []

    def health_check(self) -> dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态
        """
        try:
            start = time.perf_counter()
            self.redis_client.ping()
            latency_ms = (time.perf_counter() - start) * 1000

            return {
                "status": "ok",
                "latency_ms": round(latency_ms, 2),
            }
        except redis.RedisError as e:
            return {
                "status": "error",
                "message": str(e),
            }

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据
        """
        try:
            info = self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "total_connections_received": info.get("total_connections_received", 0),
            }
        except redis.RedisError:
            return {}


# 全局会话管理器
_session_manager: RedisSessionManager | None = None


def get_redis_session_manager() -> RedisSessionManager:
    """获取 Redis 会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = RedisSessionManager()
    return _session_manager
