"""
数据库模型定义
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    """
    用户模型
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 用户画像
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)  # cm
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)  # kg
    fitness_goal: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 减脂/增肌/塑形
    fitness_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 初级/中级/高级

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    training_plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Conversation(Base):
    """
    对话模型
    """
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user: Mapped["User | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session_id='{self.session_id}')>"


class Message(Base):
    """
    消息模型
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id"), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user/assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 意图和路由信息
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    route: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 工具调用记录
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role='{self.role}')>"


class TrainingPlan(Base):
    """
    训练计划模型
    """
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # 计划基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    goal: Mapped[str] = mapped_column(String(20), nullable=False)  # 减脂/增肌/塑形
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # 初级/中级/高级
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)  # 每周训练天数

    # 计划详情
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # 完整的周计划

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user: Mapped["User | None"] = relationship(back_populates="training_plans")

    def __repr__(self) -> str:
        return f"<TrainingPlan(id={self.id}, name='{self.name}')>"


class UserMetrics(Base):
    """
    用户身体指标记录
    """
    __tablename__ = "user_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # 指标数据
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmr: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 测量信息
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserMetrics(id={self.id}, user_id={self.user_id})>"
