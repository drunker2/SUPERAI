"""
对话 API 路由
集成 Agent 状态机处理对话
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.api.deps import RequestId, CurrentUser, ClientIP
from app.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatData,
    ChatErrorResponse,
    MessageItem,
    ChatHistoryResponse,
    SessionListResponse,
    SessionInfo,
)
from app.agent.graph import run_agent
from app.agent.memory import get_redis_session_manager, RedisChatMessageHistory
from app.utils import get_logger, bind_context

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["对话"])


def generate_session_id() -> str:
    """生成会话 ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"


@router.post(
    "/",
    response_model=ChatResponse,
    summary="发送消息",
    description="""
发送消息并获取 AI 回复。

## 支持的意图类型
- **fitness_consult**: 健身咨询（减脂、增肌、塑形等）
- **plan_request**: 训练计划生成
- **body_metrics**: 身体指标计算（BMI、BMR、体脂率）
- **nutrition_consult**: 营养咨询
- **exercise_guide**: 动作指导（深蹲、卧推等）
- **chitchat**: 闲聊

## 处理流程
1. 意图识别：分析用户输入意图
2. 路由决策：根据意图选择处理方式
   - knowledge: 知识库检索 (RAG)
   - tool: 工具调用 (BMI/BMR计算等)
   - chat: 直接对话
3. 响应生成：生成最终回复
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
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
                }
            }
        },
        400: {"model": ChatErrorResponse, "description": "请求参数错误"},
        429: {"model": ChatErrorResponse, "description": "请求过于频繁，请稍后重试"},
        500: {"model": ChatErrorResponse, "description": "服务器内部错误"},
    },
)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    trace_id: RequestId,
    user: CurrentUser,
    client_ip: ClientIP,
):
    """
    发送消息并获取回复

    - **query**: 用户输入内容，1-500 字符
    - **session_id**: 会话 ID，用于多轮对话。不传则自动创建新会话
    - **user_id**: 用户 ID，用于个性化推荐
    - **stream**: 是否流式返回（暂不支持，请使用 /chat/stream 端点）
    """
    # 绑定日志上下文
    bind_context(
        trace_id=trace_id,
        query_length=len(chat_request.query),
        client_ip=client_ip,
    )

    # 获取 Redis 会话管理器
    session_manager = get_redis_session_manager()

    # 获取或创建会话 ID
    if chat_request.session_id:
        session_id = chat_request.session_id
        # 检查会话是否存在
        if not session_manager.session_exists(session_id):
            # 会话不存在，创建新会话
            pass  # Redis 会自动创建
    else:
        session_id = generate_session_id()

    # 获取会话历史
    chat_history = session_manager.get_session(session_id)
    history_messages = chat_history.get_recent_messages(10)

    # 转换为 Agent 需要的格式
    history = [
        {"role": msg.type, "content": msg.content}
        for msg in history_messages
    ]

    logger.info(
        "对话请求",
        session_id=session_id,
        query=chat_request.query[:50] + "..." if len(chat_request.query) > 50 else chat_request.query,
        history_count=len(history),
    )

    # 保存用户消息
    chat_history.add_message(HumanMessage(content=chat_request.query))

    # 获取用户 ID
    user_id = chat_request.user_id or (user.get("user_id") if user else None)

    try:
        # 调用 Agent 处理
        result = await run_agent(
            query=chat_request.query,
            session_id=session_id,
            user_id=user_id,
            history=history if history else None,
        )

        assistant_message = result.get("response", "抱歉，我无法处理您的请求。")
        intent = result.get("intent", "unknown")
        route = result.get("route", "chat")

    except Exception as e:
        logger.error(
            "Agent 处理失败",
            error=str(e),
            session_id=session_id,
        )
        return ChatResponse(
            code=1001,
            message="AI 服务暂时不可用，请稍后重试",
            data=ChatData(
                response="",
                session_id=session_id,
                trace_id=trace_id,
            ),
        )

    # 保存助手消息
    chat_history.add_message(AIMessage(content=assistant_message))

    logger.info(
        "对话完成",
        session_id=session_id,
        response_length=len(assistant_message),
        intent=intent,
        route=route,
    )

    return ChatResponse(
        code=0,
        message="success",
        data=ChatData(
            response=assistant_message,
            session_id=session_id,
            trace_id=trace_id,
        ),
    )


@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="获取历史消息",
    description="""
获取指定会话的历史消息记录。

消息按时间正序排列，最多返回最近的消息（受 limit 参数限制）。
会话默认保留 7 天（可通过 REDIS_SESSION_TTL 配置）。
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "sess_abc123def456",
                        "messages": [
                            {"role": "user", "content": "我想减脂", "timestamp": "2024-01-15T10:30:00"},
                            {"role": "assistant", "content": "减脂的核心...", "timestamp": "2024-01-15T10:30:05"},
                        ],
                        "total": 2,
                    }
                }
            }
        },
        404: {"description": "会话不存在"},
    },
)
async def get_history(
    session_id: str,
    limit: int = 20,
):
    """
    获取会话历史消息

    - **session_id**: 会话 ID（路径参数）
    - **limit**: 返回消息数量，默认 20，最大 100
    """
    session_manager = get_redis_session_manager()
    chat_history = session_manager.get_session(session_id)
    messages = chat_history.get_recent_messages(limit)

    # 检查会话是否存在（消息为空不代表不存在）
    if not messages and not session_manager.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在",
        )

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            MessageItem(
                role=msg.type,
                content=msg.content,
                timestamp=datetime.now(),  # Redis 存储不包含时间戳
            )
            for msg in messages
        ],
        total=len(messages),
    )


@router.delete(
    "/history/{session_id}",
    summary="清空会话历史",
    description="""
清空指定会话的历史消息记录。

保留会话 ID，仅清除消息内容。后续可以继续在该会话中对话。
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {"message": "会话历史已清空", "session_id": "sess_abc123def456"}
                }
            }
        },
    },
)
async def clear_history(session_id: str):
    """
    清空会话历史

    - **session_id**: 会话 ID（路径参数）

    注意：此操作不可恢复
    """
    session_manager = get_redis_session_manager()
    success = session_manager.clear_session(session_id)

    logger.info("会话历史已清空", session_id=session_id)

    return {"message": "会话历史已清空", "session_id": session_id}


@router.delete(
    "/sessions/{session_id}",
    summary="删除会话",
    description="""
删除指定会话及其所有历史消息。

此操作会完全删除会话，包括会话 ID 和所有消息记录。
注意：此操作不可恢复。
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {"message": "会话已删除", "session_id": "sess_abc123def456"}
                }
            }
        },
    },
)
async def delete_session(session_id: str):
    """
    删除会话

    - **session_id**: 会话 ID（路径参数）

    注意：此操作会删除会话及所有历史消息，不可恢复
    """
    session_manager = get_redis_session_manager()
    session_manager.delete_session(session_id)

    logger.info("会话已删除", session_id=session_id)

    return {"message": "会话已删除", "session_id": session_id}
