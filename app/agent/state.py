"""
Agent 状态定义
LangGraph 状态机的核心状态结构
"""

from enum import Enum
from typing import Annotated, Any, TypedDict, cast

from typing_extensions import NotRequired
from langgraph.graph.message import add_messages


# ==================== 枚举定义 ====================


class IntentType(str, Enum):
    """意图类型枚举"""

    FITNESS_CONSULT = "fitness_consult"      # 健身咨询
    PLAN_REQUEST = "plan_request"            # 训练计划请求
    BODY_METRICS = "body_metrics"            # 身体指标计算
    NUTRITION_CONSULT = "nutrition_consult"  # 营养咨询
    EXERCISE_GUIDE = "exercise_guide"        # 动作指导
    DATA_RECORD = "data_record"              # 数据记录
    CHITCHAT = "chitchat"                    # 闲聊
    UNKNOWN = "unknown"                      # 未知意图


class RouteType(str, Enum):
    """路由类型枚举"""

    KNOWLEDGE = "knowledge"  # 知识库检索
    TOOL = "tool"           # 工具调用
    MCP = "mcp"             # MCP 服务调用
    CHAT = "chat"           # 直接对话


class NodeType(str, Enum):
    """节点类型枚举"""

    INTENT = "intent"           # 意图识别
    ROUTER = "router"           # 路由分发
    RETRIEVER = "retriever"     # 知识检索
    TOOL_EXECUTOR = "tool_executor"  # 工具执行
    MCP_EXECUTOR = "mcp_executor"    # MCP 调用
    GENERATOR = "generator"     # 响应生成
    ERROR_HANDLER = "error_handler"  # 错误处理


# ==================== 消息类型 ====================


class MessageRole(str, Enum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


# ==================== 状态定义 ====================


class AgentState(TypedDict):
    """
    Agent 状态定义

    LangGraph 状态机的核心状态结构，贯穿整个对话流程。

    状态流转:
    1. 输入层: query, session_id, user_id
    2. 意图识别: intent, intent_confidence, entities
    3. 路由层: route
    4. 执行层: retrieved_docs, tool_calls, mcp_calls
    5. 输出层: response, sources
    6. 上下文: messages
    7. 元数据: current_node, errors
    """

    # ==================== 输入层 ====================

    query: str
    """用户输入 (必填)"""

    session_id: str
    """会话 ID (必填)"""

    user_id: NotRequired[str]
    """用户 ID (可选，用于个性化)"""

    # ==================== 意图识别层 ====================

    intent: NotRequired[str]
    """识别到的意图类型"""

    intent_confidence: NotRequired[float]
    """意图识别置信度 (0-1)"""

    entities: NotRequired[dict[str, Any]]
    """从用户输入中提取的实体"""

    # ==================== 路由层 ====================

    route: NotRequired[str]
    """路由目标: knowledge / tool / mcp / chat"""

    # ==================== 执行层 - 知识检索 ====================

    retrieved_docs: NotRequired[list[dict[str, Any]]]
    """检索到的文档列表"""

    retrieval_scores: NotRequired[list[float]]
    """检索相关性分数"""

    # ==================== 执行层 - 工具调用 ====================

    tool_calls: NotRequired[list[dict[str, Any]]]
    """工具调用记录 (累加)"""

    tool_results: NotRequired[list[dict[str, Any]]]
    """工具执行结果 (累加)"""

    # ==================== 执行层 - MCP 调用 ====================

    mcp_calls: NotRequired[list[dict[str, Any]]]
    """MCP 调用记录 (累加)"""

    mcp_results: NotRequired[list[dict[str, Any]]]
    """MCP 执行结果 (累加)"""

    # ==================== 输出层 ====================

    response: NotRequired[str]
    """最终生成的响应"""

    sources: NotRequired[list[dict[str, Any]]]
    """引用来源"""

    # ==================== 上下文 ====================

    messages: Annotated[list[dict[str, Any]], add_messages]
    """对话历史 (自动累加消息)"""

    # ==================== 元数据 ====================

    current_node: NotRequired[str]
    """当前执行的节点名称"""

    retry_count: NotRequired[int]
    """重试次数"""

    errors: NotRequired[list[str]]
    """错误信息列表"""

    metadata: NotRequired[dict[str, Any]]
    """其他元数据"""


# ==================== 状态工厂函数 ====================


def create_initial_state(
    query: str,
    session_id: str,
    user_id: str | None = None,
) -> AgentState:
    """
    创建初始状态

    Args:
        query: 用户输入
        session_id: 会话 ID
        user_id: 用户 ID (可选)

    Returns:
        初始化的 AgentState
    """
    state: AgentState = {
        "query": query,
        "session_id": session_id,
        "messages": [],
    }

    if user_id:
        state["user_id"] = user_id

    return state


def create_state_from_history(
    query: str,
    session_id: str,
    history: list[dict[str, Any]],
    user_id: str | None = None,
) -> AgentState:
    """
    从历史消息创建状态

    Args:
        query: 用户输入
        session_id: 会话 ID
        history: 历史消息列表
        user_id: 用户 ID (可选)

    Returns:
        包含历史消息的 AgentState
    """
    state = create_initial_state(query, session_id, user_id)
    state["messages"] = history.copy()
    return state


# ==================== 状态更新工具 ====================


def update_state_intent(
    state: AgentState,
    intent: str,
    confidence: float,
    entities: dict[str, Any] | None = None,
) -> AgentState:
    """
    更新意图识别结果

    Args:
        state: 当前状态
        intent: 意图类型
        confidence: 置信度
        entities: 提取的实体

    Returns:
        更新后的状态
    """
    state["intent"] = intent
    state["intent_confidence"] = confidence
    if entities:
        state["entities"] = entities
    return state


def update_state_route(
    state: AgentState,
    route: str,
) -> AgentState:
    """
    更新路由决策

    Args:
        state: 当前状态
        route: 路由目标

    Returns:
        更新后的状态
    """
    state["route"] = route
    return state


def update_state_error(
    state: AgentState,
    error: str,
) -> AgentState:
    """
    添加错误信息

    Args:
        state: 当前状态
        error: 错误信息

    Returns:
        更新后的状态
    """
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append(error)
    return state


def add_tool_call(
    state: AgentState,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any] | None = None,
) -> AgentState:
    """
    添加工具调用记录

    Args:
        state: 当前状态
        tool_name: 工具名称
        tool_args: 工具参数
        tool_result: 工具结果 (可选)

    Returns:
        更新后的状态
    """
    if "tool_calls" not in state:
        state["tool_calls"] = []

    call_record = {
        "tool_name": tool_name,
        "tool_args": tool_args,
    }
    state["tool_calls"].append(call_record)

    if tool_result:
        if "tool_results" not in state:
            state["tool_results"] = []
        state["tool_results"].append({
            "tool_name": tool_name,
            "result": tool_result,
        })

    return state


def add_mcp_call(
    state: AgentState,
    service_name: str,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any] | None = None,
) -> AgentState:
    """
    添加 MCP 调用记录

    Args:
        state: 当前状态
        service_name: MCP 服务名称
        tool_name: 工具名称
        tool_args: 工具参数
        tool_result: 工具结果 (可选)

    Returns:
        更新后的状态
    """
    if "mcp_calls" not in state:
        state["mcp_calls"] = []

    call_record = {
        "service_name": service_name,
        "tool_name": tool_name,
        "tool_args": tool_args,
    }
    state["mcp_calls"].append(call_record)

    if tool_result:
        if "mcp_results" not in state:
            state["mcp_results"] = []
        state["mcp_results"].append({
            "service_name": service_name,
            "tool_name": tool_name,
            "result": tool_result,
        })

    return state


def add_retrieved_docs(
    state: AgentState,
    docs: list[dict[str, Any]],
    scores: list[float] | None = None,
) -> AgentState:
    """
    添加检索到的文档

    Args:
        state: 当前状态
        docs: 检索到的文档列表
        scores: 相关性分数列表

    Returns:
        更新后的状态
    """
    state["retrieved_docs"] = docs
    if scores:
        state["retrieval_scores"] = scores
    return state


def set_response(
    state: AgentState,
    response: str,
    sources: list[dict[str, Any]] | None = None,
) -> AgentState:
    """
    设置最终响应

    Args:
        state: 当前状态
        response: 生成的响应
        sources: 引用来源

    Returns:
        更新后的状态
    """
    state["response"] = response
    if sources:
        state["sources"] = sources
    return state


# ==================== 状态查询工具 ====================


def get_intent(state: AgentState) -> str | None:
    """获取意图类型"""
    return cast(str | None, state.get("intent"))


def get_route(state: AgentState) -> str | None:
    """获取路由目标"""
    return cast(str | None, state.get("route"))


def has_errors(state: AgentState) -> bool:
    """检查是否有错误"""
    return bool(state.get("errors"))


def get_errors(state: AgentState) -> list[str]:
    """获取错误列表"""
    return cast(list[str], state.get("errors", []))


def get_tool_results(state: AgentState) -> list[dict[str, Any]]:
    """获取工具执行结果"""
    return cast(list[dict[str, Any]], state.get("tool_results", []))


def get_mcp_results(state: AgentState) -> list[dict[str, Any]]:
    """获取 MCP 执行结果"""
    return cast(list[dict[str, Any]], state.get("mcp_results", []))


def get_retrieved_docs(state: AgentState) -> list[dict[str, Any]]:
    """获取检索到的文档"""
    return cast(list[dict[str, Any]], state.get("retrieved_docs", []))


def get_response(state: AgentState) -> str | None:
    """获取最终响应"""
    return cast(str | None, state.get("response"))


def get_messages(state: AgentState) -> list[dict[str, Any]]:
    """获取对话历史"""
    return cast(list[dict[str, Any]], state.get("messages", []))


def get_user_id(state: AgentState) -> str | None:
    """获取用户 ID"""
    return cast(str | None, state.get("user_id"))


def get_session_id(state: AgentState) -> str:
    """获取会话 ID"""
    return state["session_id"]


# ==================== 状态调试工具 ====================


def state_to_dict(state: AgentState) -> dict[str, Any]:
    """
    将状态转换为字典 (用于调试和日志)

    Args:
        state: Agent 状态

    Returns:
        可序列化的字典
    """
    result: dict[str, Any] = {}

    for key, value in state.items():
        if value is None:
            continue

        # 跳过过长的消息列表
        if key == "messages" and isinstance(value, list) and len(value) > 5:
            result[key] = f"[{len(value)} messages]"
        # 跳过过长的文档列表
        elif key in ("retrieved_docs", "tool_results", "mcp_results") and isinstance(value, list) and len(value) > 3:
            result[key] = f"[{len(value)} items]"
        else:
            result[key] = value

    return result


def print_state(state: AgentState, title: str = "Agent State") -> None:
    """
    打印状态信息 (用于调试)

    Args:
        state: Agent 状态
        title: 标题
    """
    import json

    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(json.dumps(state_to_dict(state), indent=2, ensure_ascii=False, default=str))
    print(f"{'='*50}\n")
