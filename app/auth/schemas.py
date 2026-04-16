"""
认证相关 Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """用户注册请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "fitness_user",
                    "email": "user@example.com",
                    "password": "securePassword123",
                }
            ]
        }
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名，3-50个字符，支持字母、数字、下划线",
        examples=["fitness_user"],
    )
    email: EmailStr = Field(
        ...,
        description="邮箱地址，用于找回密码和通知",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="密码，6-100个字符，建议包含字母和数字",
        examples=["securePassword123"],
    )


class UserLogin(BaseModel):
    """用户登录请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "fitness_user",
                    "password": "securePassword123",
                }
            ]
        }
    )

    username: str = Field(
        ...,
        description="用户名",
        examples=["fitness_user"],
    )
    password: str = Field(
        ...,
        description="密码",
        examples=["securePassword123"],
    )


class Token(BaseModel):
    """Token 响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 7200,
                }
            ]
        }
    )

    access_token: str = Field(
        ...,
        description="JWT 访问令牌，用于后续 API 认证",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="令牌类型，固定为 bearer",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="令牌有效期（秒），默认 7200 秒（2小时）",
        examples=[7200],
    )


class UserResponse(BaseModel):
    """用户信息响应"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "username": "fitness_user",
                    "email": "user@example.com",
                    "is_active": True,
                    "age": 28,
                    "gender": "male",
                    "height": 175.0,
                    "weight": 70.0,
                    "fitness_goal": "减脂",
                    "fitness_level": "中级",
                    "created_at": "2024-01-15T10:00:00",
                }
            ]
        }
    )

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    is_active: bool = Field(..., description="账号是否激活")

    # 用户画像
    age: int | None = Field(default=None, description="年龄", ge=1, le=120)
    gender: str | None = Field(default=None, description="性别: male/female")
    height: float | None = Field(default=None, description="身高 (cm)", ge=50, le=250)
    weight: float | None = Field(default=None, description="体重 (kg)", ge=20, le=300)
    fitness_goal: str | None = Field(
        default=None,
        description="健身目标: 减脂/增肌/塑形/维持",
        examples=["减脂", "增肌", "塑形"],
    )
    fitness_level: str | None = Field(
        default=None,
        description="健身水平: 初级/中级/高级",
        examples=["初级", "中级", "高级"],
    )

    created_at: datetime = Field(..., description="账号创建时间")


class UserUpdate(BaseModel):
    """用户信息更新"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "age": 28,
                    "gender": "male",
                    "height": 175.0,
                    "weight": 70.0,
                    "fitness_goal": "减脂",
                    "fitness_level": "中级",
                }
            ]
        }
    )

    age: int | None = Field(default=None, description="年龄", ge=1, le=120)
    gender: str | None = Field(default=None, description="性别: male/female")
    height: float | None = Field(default=None, description="身高 (cm)", ge=50, le=250)
    weight: float | None = Field(default=None, description="体重 (kg)", ge=20, le=300)
    fitness_goal: str | None = Field(
        default=None,
        description="健身目标: 减脂/增肌/塑形/维持",
    )
    fitness_level: str | None = Field(
        default=None,
        description="健身水平: 初级/中级/高级",
    )


class TokenData(BaseModel):
    """Token 数据"""

    user_id: int | None = Field(default=None, description="用户 ID")
    username: str | None = Field(default=None, description="用户名")
