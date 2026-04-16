"""
认证服务

处理用户注册、登录、Token 生成等
"""

from datetime import datetime, timedelta
from typing import Any
import hashlib
import secrets

from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.auth.schemas import UserCreate, Token, TokenData
from app.utils import get_logger

logger = get_logger(__name__)


def _hash_password(password: str) -> str:
    """使用 SHA256 哈希密码"""
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hash_value}"


def _verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    try:
        salt, hash_value = hashed.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
    except ValueError:
        return False


class AuthService:
    """
    认证服务

    Features:
    - 用户注册
    - 用户登录
    - Token 生成和验证
    - 密码加密
    """

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire = settings.jwt_access_token_expire_minutes

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return _verify_password(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return _hash_password(password)

    def create_access_token(self, data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """
        创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量

        Returns:
            JWT Token
        """
        to_encode = data.copy()

        # 确保 sub 是字符串
        if "sub" in to_encode and isinstance(to_encode["sub"], int):
            to_encode["sub"] = str(to_encode["sub"])

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def decode_token(self, token: str) -> TokenData | None:
        """
        解码令牌

        Args:
            token: JWT Token

        Returns:
            TokenData 或 None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id_str: str = payload.get("sub")
            username: str = payload.get("username")

            if user_id_str is None:
                return None

            # 将字符串 ID 转换为整数
            user_id = int(user_id_str)

            return TokenData(user_id=user_id, username=username)

        except JWTError as e:
            logger.warning("Token 解码失败", error=str(e))
            return None

    async def register_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """
        注册新用户

        Args:
            db: 数据库会话
            user_data: 用户注册数据

        Returns:
            创建的用户

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否存在
        result = await db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 检查邮箱是否存在
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ValueError("邮箱已被注册")

        # 创建用户
        hashed_password = self.get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("用户注册成功", user_id=user.id, username=user.username)

        return user

    async def authenticate_user(self, db: AsyncSession, username: str, password: str) -> User | None:
        """
        验证用户

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            用户对象或 None
        """
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user

    async def login(self, db: AsyncSession, username: str, password: str) -> Token | None:
        """
        用户登录

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            Token 或 None
        """
        user = await self.authenticate_user(db, username, password)

        if not user:
            return None

        # 生成 Token
        access_token = self.create_access_token(
            data={"sub": user.id, "username": user.username}
        )

        logger.info("用户登录成功", user_id=user.id, username=user.username)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire * 60,
        )

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        """根据 ID 获取用户"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user_profile(
        self,
        db: AsyncSession,
        user_id: int,
        **kwargs: Any,
    ) -> User | None:
        """
        更新用户画像

        Args:
            db: 数据库会话
            user_id: 用户 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的用户
        """
        user = await self.get_user_by_id(db, user_id)

        if not user:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        logger.info("用户画像更新", user_id=user_id)

        return user


# 全局服务实例
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
