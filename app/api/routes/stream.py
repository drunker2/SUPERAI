"""
流式响应 API 路由
"""

import json
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.api.deps import RequestId, CurrentUser, ClientIP
from app.api.schemas.chat import ChatRequest
from app.llm import QwenLLM
from app.agent.memory import get_redis_session_manager
from app.utils import get_logger, bind_context
from app.utils.metrics import record_chat_request, record_error

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["对话"])


async def generate_stream(
    query: str,
    session_id: str,
    trace_id: str,
    history: list | None = None,
):
    """
    生成流式响应

    Args:
        query: 用户输入
        session_id: 会话 ID
        trace_id: 追踪 ID
        history: 历史消息
    """
    from langchain_core.messages import HumanMessage, AIMessage

    start_time = time.perf_counter()
    bind_context(session_id=session_id, trace_id=trace_id)

    # 获取 LLM 实例
    llm = QwenLLM()

    # 构建历史消息
    messages = []
    if history:
        for msg in history[-10:]:  # 只保留最近 10 条
            role = msg.get("type") or msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("human", "user"):
                messages.append(HumanMessage(content=content))
            elif role in ("ai", "assistant"):
                messages.append(AIMessage(content=content))

    # 发送开始事件
    yield {
        "event": "start",
        "data": json.dumps({"session_id": session_id, "trace_id": trace_id}),
    }

    try:
        # 调用 LLM 流式接口
        full_response = ""
        async for chunk in llm.astream(prompt=query, history=messages if messages else None):
            if chunk and chunk.content:
                full_response += chunk.content
                yield {
                    "event": "token",
                    "data": json.dumps({"content": chunk.content}),
                }

        # 保存消息到 Redis
        session_manager = get_redis_session_manager()
        chat_history = session_manager.get_session(session_id)
        chat_history.add_message(HumanMessage(content=query))
        chat_history.add_message(AIMessage(content=full_response))

        # 计算延迟
        latency_seconds = time.perf_counter() - start_time

        # 记录 Prometheus 指标
        record_chat_request(
            session_id=session_id,
            intent="chat",  # 流式端点暂不进行意图识别
            status="success",
            latency_seconds=latency_seconds,
        )

        # 发送完成事件
        yield {
            "event": "done",
            "data": json.dumps({
                "session_id": session_id,
                "response_length": len(full_response),
            }),
        }

        logger.info(
            "流式对话完成",
            session_id=session_id,
            response_length=len(full_response),
            latency_seconds=round(latency_seconds, 2),
        )

    except Exception as e:
        latency_seconds = time.perf_counter() - start_time
        logger.error("流式响应失败", error=str(e), session_id=session_id)

        # 记录错误指标
        record_chat_request(
            session_id=session_id,
            intent="chat",
            status="error",
            latency_seconds=latency_seconds,
        )
        record_error(error_type=type(e).__name__, endpoint="/chat/stream")

        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }


@router.get(
    "/stream",
    summary="流式对话 (GET)",
    description="""
使用 Server-Sent Events (SSE) 实现流式对话响应。

## SSE 事件类型
| 事件 | 说明 | 数据格式 |
|------|------|----------|
| start | 对话开始 | `{"session_id": "xxx", "trace_id": "xxx"}` |
| token | 文本片段 | `{"content": "文本内容"}` |
| done | 对话完成 | `{"session_id": "xxx", "response_length": 100}` |
| error | 发生错误 | `{"error": "错误信息"}` |

## 使用示例
```javascript
const eventSource = new EventSource('/chat/stream?query=你好&session_id=sess_123');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.content) {
    console.log(data.content);
  }
};
```

## 注意事项
- 此端点不进行意图识别，直接调用 LLM
- 建议使用 POST 版本以支持更长的查询内容
""",
    responses={
        200: {
            "description": "SSE 流",
            "content": {
                "text/event-stream": {
                    "example": """event: start
data: {"session_id": "sess_abc123", "trace_id": "req_xyz"}

event: token
data: {"content": "减脂"}

event: token
data: {"content": "的核心"}

event: done
data: {"session_id": "sess_abc123", "response_length": 100}
"""
                }
            }
        },
    },
)
async def chat_stream(
    request: Request,
    query: str,
    session_id: str | None = None,
    trace_id: RequestId = "",
    user: CurrentUser = None,
    client_ip: ClientIP = "",
):
    """
    流式对话接口 (GET)

    使用 Server-Sent Events (SSE) 实现流式响应。

    - **query**: 用户输入内容
    - **session_id**: 会话 ID，不传则自动创建
    """
    import uuid

    # 生成或使用现有会话 ID
    if not session_id:
        session_id = f"sess_{uuid.uuid4().hex[:16]}"

    bind_context(trace_id=trace_id, client_ip=client_ip)

    logger.info(
        "流式对话请求",
        session_id=session_id,
        query=query[:50] if len(query) > 50 else query,
    )

    # 获取历史消息
    history = None
    session_manager = get_redis_session_manager()
    if session_manager.session_exists(session_id):
        chat_history = session_manager.get_session(session_id)
        history_messages = chat_history.get_recent_messages(10)
        history = [
            {"type": msg.type, "content": msg.content}
            for msg in history_messages
        ]

    return EventSourceResponse(
        generate_stream(
            query=query,
            session_id=session_id,
            trace_id=trace_id,
            history=history,
        ),
        media_type="text/event-stream",
    )


@router.post(
    "/stream",
    summary="流式对话 (POST)",
    description="""
使用 Server-Sent Events (SSE) 实现流式对话响应 (POST 版本)。

## 与 GET 版本的区别
- 支持更长的查询内容（不受 URL 长度限制）
- 支持传递更多参数（user_id 等）
- 请求体格式与 /chat 端点一致

## SSE 事件类型
| 事件 | 说明 | 数据格式 |
|------|------|----------|
| start | 对话开始 | `{"session_id": "xxx", "trace_id": "xxx"}` |
| token | 文本片段 | `{"content": "文本内容"}` |
| done | 对话完成 | `{"session_id": "xxx", "response_length": 100}` |
| error | 发生错误 | `{"error": "错误信息"}` |

## 使用示例
```javascript
const response = await fetch('/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: '我想了解深蹲的标准动作',
    session_id: 'sess_123'
  })
});
const reader = response.body.getReader();
// 处理 SSE 流...
```
""",
    responses={
        200: {
            "description": "SSE 流",
            "content": {
                "text/event-stream": {
                    "example": """event: start
data: {"session_id": "sess_abc123", "trace_id": "req_xyz"}

event: token
data: {"content": "深蹲"}

event: token
data: {"content": "是复合动作"}

event: done
data: {"session_id": "sess_abc123", "response_length": 200}
"""
                }
            }
        },
    },
)
async def chat_stream_post(
    request: Request,
    chat_request: ChatRequest,
    trace_id: RequestId = "",
    user: CurrentUser = None,
    client_ip: ClientIP = "",
):
    """
    流式对话接口 (POST 版本)

    使用 Server-Sent Events (SSE) 实现流式响应。
    建议用于较长查询内容的场景。
    """
    import uuid

    query = chat_request.query
    session_id = chat_request.session_id or f"sess_{uuid.uuid4().hex[:16]}"

    bind_context(trace_id=trace_id, client_ip=client_ip)

    logger.info(
        "流式对话请求 (POST)",
        session_id=session_id,
        query=query[:50] if len(query) > 50 else query,
    )

    # 获取历史消息
    history = chat_request.history if hasattr(chat_request, 'history') else None

    return EventSourceResponse(
        generate_stream(
            query=query,
            session_id=session_id,
            trace_id=trace_id,
            history=history,
        ),
        media_type="text/event-stream",
    )
