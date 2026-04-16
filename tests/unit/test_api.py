"""
API 路由单元测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.chat import router as chat_router
from app.api.routes.stream import router as stream_router
from app.api.routes.metrics import router as metrics_router


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestMetricsEndpoint:
    """指标端点测试"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_metrics_endpoint(self, client):
        """测试 Prometheus 指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # 检查是否包含基础指标
        content = response.text
        assert "python_info" in content
        assert "chat_requests_total" in content
        assert "llm_latency_seconds" in content


class TestToolsEndpoint:
    """工具端点测试"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_list_tools(self, client):
        """测试工具列表"""
        response = client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        # 检查注册的工具
        tool_names = [t["name"] for t in data["tools"]]
        assert "calculate_bmi" in tool_names
        assert "calculate_bmr" in tool_names

    def test_tool_docs(self, client):
        """测试工具文档"""
        response = client.get("/tools/docs")
        # 可能返回 404 或重定向到 /tools
        assert response.status_code in [200, 404]


class TestAuthSchemas:
    """认证 Schema 测试"""

    def test_user_create_valid(self):
        """测试用户创建验证"""
        from app.auth.schemas import UserCreate

        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_create_short_username(self):
        """测试用户名太短"""
        from app.auth.schemas import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",
                email="test@example.com",
                password="password123",
            )

    def test_user_create_short_password(self):
        """测试密码太短"""
        from app.auth.schemas import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="12345",
            )

    def test_token_model(self):
        """测试 Token 模型"""
        from app.auth.schemas import Token

        token = Token(
            access_token="test_token",
            token_type="bearer",
            expires_in=3600,
        )
        assert token.access_token == "test_token"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600

    def test_user_response_model(self):
        """测试用户响应模型"""
        from app.auth.schemas import UserResponse
        from datetime import datetime

        user = UserResponse(
            id=1,
            username="testuser",
            email="test@example.com",
            is_active=True,
            created_at=datetime.now(),
        )
        assert user.id == 1
        assert user.username == "testuser"


class TestChatSchemas:
    """对话 Schema 测试"""

    def test_chat_request_valid(self):
        """测试对话请求"""
        from app.api.schemas.chat import ChatRequest

        request = ChatRequest(query="你好")
        assert request.query == "你好"
        assert request.session_id is None

    def test_chat_request_with_session(self):
        """测试带会话 ID 的对话请求"""
        from app.api.schemas.chat import ChatRequest

        request = ChatRequest(
            query="你好",
            session_id="test-session-123",
        )
        assert request.query == "你好"
        assert request.session_id == "test-session-123"

    def test_chat_response(self):
        """测试对话响应"""
        from app.api.schemas.chat import ChatResponse, ChatData

        response = ChatResponse(
            data=ChatData(
                response="你好！有什么可以帮助你的？",
                session_id="test-session",
            )
        )
        assert response.data.response == "你好！有什么可以帮助你的？"
        assert response.data.session_id == "test-session"
