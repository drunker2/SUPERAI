"""
响应生成节点
根据上下文生成最终响应
"""

import time
from typing import Any

from app.agent.state import (
    AgentState,
    set_response,
    update_state_error,
)
from app.llm import QwenLLM, LLMResponse, QwenAPIError
from app.utils import get_logger, bind_context

logger = get_logger(__name__)

# LLM 实例
_llm: QwenLLM | None = None


def get_llm() -> QwenLLM:
    """获取 LLM 实例"""
    global _llm
    if _llm is None:
        _llm = QwenLLM()
    return _llm


# 系统提示词
GENERATOR_SYSTEM_PROMPT = """你是一个专业的健身助手，能够为用户提供：
1. 健身知识咨询 - 解答健身相关问题
2. 训练计划制定 - 根据用户目标制定个性化计划
3. 动作指导 - 详细讲解动作要领和注意事项
4. 营养建议 - 提供合理的饮食建议
5. 数据记录 - 帮助用户记录训练数据

请用友好、专业的语气回答用户问题。如果问题涉及医疗健康，请提醒用户咨询专业医生。

回答要简洁明了，不要过于冗长。"""


async def generator_node(state: AgentState) -> AgentState:
    """
    响应生成节点

    根据对话历史和检索/执行结果生成最终响应

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态（包含 response 字段）
    """
    query = state["query"]
    session_id = state["session_id"]
    messages = state.get("messages", [])

    bind_context(node="generator", session_id=session_id)

    start_time = time.perf_counter()
    logger.info("开始生成响应", query=query[:50])

    try:
        llm = get_llm()

        # 构建历史消息
        history = None
        if messages:
            # 只保留最近的对话历史
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            history = [
                {"role": msg.type, "content": msg.content}
                for msg in recent_messages
                if msg.content
            ]

        # 检查是否有检索结果或工具结果
        retrieved_docs = state.get("retrieved_docs", [])
        tool_results = state.get("tool_results", [])
        mcp_results = state.get("mcp_results", [])

        # 构建增强上下文
        context_parts = []
        if retrieved_docs:
            context_parts.append("【相关知识】\n" + "\n".join(
                doc.get("content", "")[:500] for doc in retrieved_docs[:3]
            ))
        if tool_results:
            context_parts.append("【工具执行结果】\n" + str(tool_results))
        if mcp_results:
            context_parts.append("【MCP服务结果】\n" + str(mcp_results))

        # 构建用户提示词
        if context_parts:
            enhanced_query = f"{query}\n\n" + "\n\n".join(context_parts)
        else:
            enhanced_query = query

        # 调用 LLM
        response: LLMResponse = await llm.ainvoke(
            prompt=enhanced_query,
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            history=history,
        )

        assistant_message = response.content

        # 更新状态
        set_response(state, assistant_message)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "响应生成完成",
            response_length=len(assistant_message),
            latency_ms=round(duration_ms, 2),
        )

        return state

    except QwenAPIError as e:
        logger.error("LLM 调用失败", error=str(e))
        update_state_error(state, f"响应生成失败: {e}")
        set_response(state, "抱歉，服务暂时不可用，请稍后重试。")
        return state

    except Exception as e:
        logger.exception("响应生成异常", error=str(e))
        update_state_error(state, f"响应生成异常: {e}")
        set_response(state, "抱歉，发生了错误，请稍后重试。")
        return state


def generator_node_sync(state: AgentState) -> AgentState:
    """
    响应生成节点（同步版本）
    """
    import asyncio
    return asyncio.run(generator_node(state))
