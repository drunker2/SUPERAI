"""
Redis 会话存储单元测试
"""

import time
import pytest

from langchain_core.messages import HumanMessage, AIMessage

from app.agent.memory import RedisChatMessageHistory, RedisSessionManager, get_redis_session_manager


class TestRedisChatMessageHistory:
    """Redis 会话历史测试"""

    @pytest.fixture
    def memory(self):
        """创建测试用的会话历史"""
        memory = RedisChatMessageHistory(
            session_id="test-session-1",
            ttl=60,  # 1 分钟过期，便于测试
        )
        yield memory
        # 清理
        memory.clear()

    def test_add_and_get_message(self, memory):
        """测试添加和获取消息"""
        memory.add_message(HumanMessage("你好"))

        messages = memory.messages
        assert len(messages) == 1
        assert messages[0].content == "你好"

    def test_add_multiple_messages(self, memory):
        """测试添加多条消息"""
        memory.add_message(HumanMessage("你好"))
        memory.add_message(AIMessage("你好！有什么可以帮你的？"))
        memory.add_message(HumanMessage("我想健身"))

        messages = memory.messages
        assert len(messages) == 3

    def test_get_recent_messages(self, memory):
        """测试获取最近消息"""
        for i in range(10):
            memory.add_message(HumanMessage(f"消息 {i}"))

        recent = memory.get_recent_messages(5)
        assert len(recent) == 5

    def test_get_message_count(self, memory):
        """测试获取消息数量"""
        assert memory.get_message_count() == 0

        memory.add_message(HumanMessage("test"))
        assert memory.get_message_count() == 1

    def test_clear(self, memory):
        """测试清空会话"""
        memory.add_message(HumanMessage("test"))
        assert memory.get_message_count() == 1

        memory.clear()
        assert memory.get_message_count() == 0

    def test_ttl(self, memory):
        """测试过期时间"""
        memory.add_message(HumanMessage("test"))
        ttl = memory.get_ttl()
        assert ttl > 0
        assert ttl <= 60

    def test_set_ttl(self, memory):
        """测试设置过期时间"""
        memory.add_message(HumanMessage("test"))
        memory.set_ttl(120)
        ttl = memory.get_ttl()
        assert ttl > 60
        assert ttl <= 120


class TestRedisSessionManager:
    """Redis 会话管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建测试用的会话管理器"""
        return RedisSessionManager(ttl=60)

    def test_get_session(self, manager):
        """测试获取会话"""
        session = manager.get_session("test-session-2")
        assert session is not None
        assert session.session_id == "test-session-2"
        session.clear()

    def test_session_exists(self, manager):
        """测试检查会话是否存在"""
        session_id = "test-session-3"

        assert manager.session_exists(session_id) is False

        session = manager.get_session(session_id)
        session.add_message(HumanMessage("test"))

        assert manager.session_exists(session_id) is True
        session.clear()

    def test_delete_session(self, manager):
        """测试删除会话"""
        session_id = "test-session-4"

        session = manager.get_session(session_id)
        session.add_message(HumanMessage("test"))

        assert manager.session_exists(session_id) is True

        manager.delete_session(session_id)
        assert manager.session_exists(session_id) is False

    def test_health_check(self, manager):
        """测试健康检查"""
        result = manager.health_check()

        assert result["status"] == "ok"
        assert "latency_ms" in result

    def test_get_stats(self, manager):
        """测试获取统计信息"""
        stats = manager.get_stats()

        assert "connected_clients" in stats


class TestGlobalSessionManager:
    """全局会话管理器测试"""

    def test_get_singleton(self):
        """测试获取单例"""
        manager1 = get_redis_session_manager()
        manager2 = get_redis_session_manager()

        assert manager1 is manager2

    def test_singleton_health_check(self):
        """测试单例健康检查"""
        manager = get_redis_session_manager()
        result = manager.health_check()

        assert result["status"] == "ok"


class TestRedisPerformance:
    """Redis 性能测试"""

    def test_100_messages_performance(self):
        """测试 100 条消息读写性能"""
        memory = RedisChatMessageHistory(session_id="perf-test", ttl=60)

        # 写入 100 条消息
        start = time.perf_counter()
        for i in range(100):
            memory.add_message(HumanMessage(f"消息 {i}"))
        write_time = (time.perf_counter() - start) * 1000

        # 读取 100 条消息
        start = time.perf_counter()
        messages = memory.messages
        read_time = (time.perf_counter() - start) * 1000

        # 清理
        memory.clear()

        # 性能要求：读写延迟 < 100ms
        assert write_time < 100, f"写入延迟 {write_time}ms 超过 100ms"
        assert read_time < 100, f"读取延迟 {read_time}ms 超过 100ms"
        assert len(messages) == 100
