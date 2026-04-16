"""
对话 API 数据模型
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ==================== 请求模型 ====================


class ChatRequest(BaseModel):
    """对话请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "我想减脂，应该怎么做？",
                    "session_id": "sess_abc123def456",
                    "user_id": "user_001",
                    "stream": False,
                },
                {
                    "query": "帮我计算一下BMI，身高175cm，体重70kg",
                    "session_id": None,
                    "user_id": None,
                    "stream": False,
                },
                {
                    "query": "深蹲的标准动作是什么？",
                    "session_id": "sess_abc123def456",
                    "user_id": "user_001",
                    "stream": False,
                },
            ]
        }
    )

    query: str = Field(
        ...,
        description="用户输入内容，支持健身咨询、训练计划、身体指标计算等",
        min_length=1,
        max_length=500,
        examples=["我想减脂，应该怎么做？", "帮我制定一个增肌训练计划"],
    )
    session_id: str | None = Field(
        default=None,
        description="会话 ID，用于保持多轮对话上下文。不传则自动创建新会话",
        examples=["sess_abc123def456"],
    )
    user_id: str | None = Field(
        default=None,
        description="用户 ID，用于个性化推荐和用户画像关联",
        examples=["user_001"],
    )
    stream: bool = Field(
        default=False,
        description="是否流式返回（当前版本暂不支持，请使用 /chat/stream 端点）",
    )


# ==================== 响应模型 ====================


class ChatData(BaseModel):
    """对话响应数据"""

    response: str = Field(
        ...,
        description="助手回复内容",
        examples=["减脂的核心在于创造热量缺口。建议你从以下几个方面入手：\n1. 饮食控制：每日热量摄入低于消耗300-500大卡\n2. 有氧运动：每周3-5次，每次30-45分钟\n3. 力量训练：保持肌肉量，提高基础代谢\n\n具体可以参考知识库中的减脂基础知识。"],
    )
    session_id: str = Field(
        ...,
        description="会话 ID，后续请求可使用此 ID 保持对话上下文",
        examples=["sess_abc123def456"],
    )
    trace_id: str | None = Field(
        default=None,
        description="追踪 ID，用于日志关联和问题排查",
        examples=["req_xyz789"],
    )
    intent: str | None = Field(
        default=None,
        description="识别的用户意图类型",
        examples=["fitness_consult", "plan_request", "body_metrics", "exercise_guide"],
    )
    route: str | None = Field(
        default=None,
        description="处理路由类型",
        examples=["knowledge", "tool", "chat"],
    )


class ChatResponse(BaseModel):
    """对话响应"""

    code: int = Field(
        default=0,
        description="状态码，0 表示成功，非 0 表示错误",
        examples=[0],
    )
    message: str = Field(
        default="success",
        description="状态信息",
        examples=["success", "参数错误", "服务异常"],
    )
    data: ChatData = Field(..., description="响应数据")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "response": "减脂的核心在于创造热量缺口...",
                        "session_id": "sess_abc123def456",
                        "trace_id": "req_xyz789",
                        "intent": "fitness_consult",
                        "route": "knowledge",
                    }
                }
            ]
        }
    )

    @classmethod
    def success(
        cls,
        response: str,
        session_id: str,
        trace_id: str | None = None,
        intent: str | None = None,
        route: str | None = None,
    ) -> "ChatResponse":
        """创建成功响应"""
        return cls(
            code=0,
            message="success",
            data=ChatData(
                response=response,
                session_id=session_id,
                trace_id=trace_id,
                intent=intent,
                route=route,
            ),
        )

    @classmethod
    def error(
        cls,
        code: int,
        message: str,
        session_id: str,
        trace_id: str | None = None,
    ) -> "ChatResponse":
        """创建错误响应"""
        return cls(
            code=code,
            message=message,
            data=ChatData(
                response="",
                session_id=session_id,
                trace_id=trace_id,
            ),
        )


class ChatErrorResponse(BaseModel):
    """对话错误响应"""

    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    trace_id: str | None = Field(default=None, description="追踪 ID")


# ==================== 历史消息模型 ====================


class MessageItem(BaseModel):
    """消息项"""

    role: str = Field(
        ...,
        description="消息角色: user(用户) / assistant(助手) / system(系统)",
        examples=["user", "assistant"],
    )
    content: str = Field(
        ...,
        description="消息内容",
        examples=["我想减脂，应该怎么做？", "减脂的核心在于创造热量缺口..."],
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="消息时间 (ISO 8601 格式)",
        examples=["2024-01-15T10:30:00"],
    )


class ChatHistoryResponse(BaseModel):
    """历史消息响应"""

    session_id: str = Field(
        ...,
        description="会话 ID",
        examples=["sess_abc123def456"],
    )
    messages: list[MessageItem] = Field(
        default_factory=list,
        description="消息列表，按时间正序排列",
    )
    total: int = Field(
        default=0,
        description="消息总数",
        examples=[10],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "sess_abc123def456",
                    "messages": [
                        {"role": "user", "content": "我想减脂", "timestamp": "2024-01-15T10:30:00"},
                        {"role": "assistant", "content": "减脂的核心...", "timestamp": "2024-01-15T10:30:05"},
                    ],
                    "total": 2,
                }
            ]
        }
    )


# ==================== 会话模型 ====================


class SessionInfo(BaseModel):
    """会话信息"""

    session_id: str = Field(
        ...,
        description="会话 ID",
        examples=["sess_abc123def456"],
    )
    created_at: datetime = Field(
        ...,
        description="创建时间",
        examples=["2024-01-15T10:00:00"],
    )
    updated_at: datetime = Field(
        ...,
        description="最后更新时间",
        examples=["2024-01-15T11:30:00"],
    )
    message_count: int = Field(
        default=0,
        description="消息数量",
        examples=[10],
    )


class SessionListResponse(BaseModel):
    """会话列表响应"""

    sessions: list[SessionInfo] = Field(
        default_factory=list,
        description="会话列表",
    )
    total: int = Field(
        default=0,
        description="会话总数",
        examples=[5],
    )
