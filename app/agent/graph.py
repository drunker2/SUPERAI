"""
LangGraph 状态机图
"""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState, create_initial_state
from app.agent.nodes import (
    intent_node,
    router_node,
    route_decision,
    generator_node,
    retriever_node,
    tool_executor_node,
    mcp_executor_node,
)
from app.utils import get_logger

logger = get_logger(__name__)


# ==================== 创建 StateGraph ====================


def create_agent_graph() -> StateGraph:
    """
    创建 Agent 状态机图

    Returns:
        配置好的 StateGraph
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # ==================== 添加节点 ====================

    workflow.add_node("intent", intent_node)
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("mcp_executor", mcp_executor_node)
    workflow.add_node("generator", generator_node)

    # ==================== 设置入口 ====================

    workflow.set_entry_point("intent")

    # ==================== 添加边 ====================

    # intent -> router
    workflow.add_edge("intent", "router")

    # router -> 条件分支 (retriever/tool_executor/mcp_executor/generator)
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
            "mcp_executor": "mcp_executor",
            "generator": "generator",
        },
    )

    # 执行节点 -> generator
    workflow.add_edge("retriever", "generator")
    workflow.add_edge("tool_executor", "generator")
    workflow.add_edge("mcp_executor", "generator")

    # generator -> END
    workflow.add_edge("generator", END)

    logger.info("Agent 状态机图创建完成")

    return workflow


# ==================== 编译图 ====================


def compile_agent_graph(checkpointer=None):
    """
    编译 Agent 状态机图

    Args:
        checkpointer: 状态持久化器 (MemorySaver 或 Redis)

    Returns:
        编译后的可执行图
    """
    workflow = create_agent_graph()

    # 暂时不使用 checkpointer，避免序列化问题
    # TODO: Phase 7 实现基于 Redis 的 checkpointer
    app = workflow.compile()

    logger.info("Agent 状态机图编译完成")

    return app


# 全局图实例
_graph = None


def get_graph():
    """获取全局图实例"""
    global _graph
    if _graph is None:
        _graph = compile_agent_graph()
    return _graph


# 导出编译后的图
graph = compile_agent_graph()


# ==================== 图可视化 ====================


def get_graph_mermaid() -> str:
    """
    获取图的 Mermaid 格式表示

    Returns:
        Mermaid 格式的图结构字符串
    """
    try:
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.error(f"生成 Mermaid 图失败: {e}")
        return ""


def save_graph_image(output_path: str = "docs/agent_graph.png") -> bool:
    """
    保存图的可视化图片

    Args:
        output_path: 输出路径

    Returns:
        是否成功
    """
    try:
        import os

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 尝试使用 PNG 格式
        try:
            from PIL import Image
            import io

            # 获取 PNG 数据
            png_data = graph.get_graph().draw_mermaid_png()
            with open(output_path, "wb") as f:
                f.write(png_data)
            logger.info(f"图可视化图片已保存: {output_path}")
            return True
        except ImportError:
            logger.warning("PIL 未安装，无法生成 PNG 图片")
            return False

    except Exception as e:
        logger.error(f"保存图可视化失败: {e}")
        return False


# ==================== 执行图 ====================


async def run_agent(
    query: str,
    session_id: str,
    user_id: str | None = None,
    history: list | None = None,
) -> dict:
    """
    运行 Agent 处理用户输入

    Args:
        query: 用户输入
        session_id: 会话 ID
        user_id: 用户 ID
        history: 历史消息

    Returns:
        处理结果
    """
    # 创建初始状态
    state = create_initial_state(query, session_id, user_id)

    if history:
        state["messages"] = history

    # 运行图 (不使用 checkpointer)
    result = await graph.ainvoke(state)

    return result


def run_agent_sync(
    query: str,
    session_id: str,
    user_id: str | None = None,
    history: list | None = None,
) -> dict:
    """
    运行 Agent (同步版本)
    """
    import asyncio
    return asyncio.run(run_agent(query, session_id, user_id, history))
