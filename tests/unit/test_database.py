"""
数据库模块单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime


class TestDatabaseModels:
    """数据库模型测试"""

    def test_user_model_creation(self):
        """测试用户模型创建"""
        from app.db.models import User

        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed123",
            is_active=True,
            is_superuser=False,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_model_with_profile(self):
        """测试用户画像"""
        from app.db.models import User

        user = User(
            username="fitness_user",
            email="fitness@example.com",
            hashed_password="hashed123",
            age=25,
            gender="male",
            height=175.0,
            weight=70.0,
            fitness_goal="减脂",
            fitness_level="中级",
        )

        assert user.age == 25
        assert user.height == 175.0
        assert user.weight == 70.0
        assert user.fitness_goal == "减脂"

    def test_conversation_model(self):
        """测试对话模型"""
        from app.db.models import Conversation

        conv = Conversation(
            session_id="test-session-123",
            user_id=1,
        )

        assert conv.session_id == "test-session-123"

    def test_message_model(self):
        """测试消息模型"""
        from app.db.models import Message

        msg = Message(
            conversation_id=1,
            role="user",
            content="你好",
        )

        assert msg.role == "user"
        assert msg.content == "你好"

    def test_training_plan_model(self):
        """测试训练计划模型"""
        from app.db.models import TrainingPlan

        plan = TrainingPlan(
            user_id=1,
            name="减脂计划",
            goal="减脂",
            level="初级",
            frequency=3,
            plan_data={"days": []},
        )

        assert plan.name == "减脂计划"
        assert plan.goal == "减脂"
        assert plan.frequency == 3

    def test_user_metrics_model(self):
        """测试用户指标模型"""
        from app.db.models import UserMetrics

        metrics = UserMetrics(
            user_id=1,
            weight=70.0,
            body_fat_percent=15.0,
            bmi=22.5,
        )

        assert metrics.weight == 70.0
        assert metrics.body_fat_percent == 15.0
        assert metrics.bmi == 22.5


class TestAuthService:
    """认证服务测试"""

    def test_password_hash(self):
        """测试密码哈希"""
        from app.auth.service import AuthService

        service = AuthService()
        password = "test123456"
        hashed = service.get_password_hash(password)

        assert hashed != password
        assert ":" in hashed  # 格式: salt:hash

    def test_password_verify(self):
        """测试密码验证"""
        from app.auth.service import AuthService

        service = AuthService()
        password = "test123456"
        hashed = service.get_password_hash(password)

        assert service.verify_password(password, hashed) is True
        assert service.verify_password("wrong_password", hashed) is False

    def test_create_token(self):
        """测试创建 Token"""
        from app.auth.service import AuthService

        service = AuthService()
        token = service.create_access_token(
            data={"sub": "1", "username": "test"}
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT 通常很长

    def test_decode_token(self):
        """测试解码 Token"""
        from app.auth.service import AuthService

        service = AuthService()
        token = service.create_access_token(
            data={"sub": "1", "username": "test"}
        )

        token_data = service.decode_token(token)

        assert token_data is not None
        assert token_data.user_id == 1
        assert token_data.username == "test"

    def test_decode_invalid_token(self):
        """测试解码无效 Token"""
        from app.auth.service import AuthService

        service = AuthService()
        token_data = service.decode_token("invalid_token")

        assert token_data is None

    def test_decode_expired_token(self):
        """测试解码过期 Token"""
        from app.auth.service import AuthService
        from datetime import timedelta

        service = AuthService()
        # 创建一个立即过期的 Token
        token = service.create_access_token(
            data={"sub": "1", "username": "test"},
            expires_delta=timedelta(seconds=-1),
        )

        # 过期 Token 解码应该失败
        token_data = service.decode_token(token)
        assert token_data is None


class TestDatabaseConnection:
    """数据库连接测试"""

    @patch('app.db.database.create_async_engine')
    def test_engine_creation(self, mock_create_engine):
        """测试引擎创建"""
        from app.db.database import engine

        # 引擎应该在模块加载时创建
        assert True  # 只要不报错就行

    def test_base_class(self):
        """测试基类"""
        from app.db.database import Base
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)


class TestAuthDependencies:
    """认证依赖测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """测试无 Token 时获取用户"""
        from app.api.deps import get_current_user

        # 模拟请求
        result = await get_current_user(None)
        assert result is None

    @pytest.mark.asyncio
    @patch('app.api.deps.settings')
    async def test_get_current_user_test_token(self, mock_settings):
        """测试测试 Token"""
        from app.api.deps import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        mock_settings.is_development = True

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token",
        )

        result = await get_current_user(credentials)
        assert result is not None
        assert result["user_id"] == "test_user"


class TestUserSchemas:
    """用户 Schema 测试"""

    def test_user_create_validation(self):
        """测试用户创建验证"""
        from app.auth.schemas import UserCreate

        user = UserCreate(
            username="valid_user",
            email="valid@example.com",
            password="validpassword123",
        )

        assert user.username == "valid_user"

    def test_user_update(self):
        """测试用户更新"""
        from app.auth.schemas import UserUpdate

        update = UserUpdate(
            age=30,
            height=180.0,
            weight=75.0,
            fitness_goal="增肌",
        )

        assert update.age == 30
        assert update.fitness_goal == "增肌"

    def test_token_data(self):
        """测试 Token 数据"""
        from app.auth.schemas import TokenData

        data = TokenData(user_id=1, username="test")
        assert data.user_id == 1
        assert data.username == "test"
