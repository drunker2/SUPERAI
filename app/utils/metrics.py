"""
Prometheus 指标模块

收集和暴露业务及系统指标
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client.registry import REGISTRY

# ==================== 业务指标 ====================

# 对话请求总数
CHAT_REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total number of chat requests",
    ["session_id", "intent", "status"],
)

# 对话延迟分布
CHAT_LATENCY_SECONDS = Histogram(
    "chat_latency_seconds",
    "Chat request latency in seconds",
    ["intent"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# 意图识别准确率 (通过 Gauge 记录)
INTENT_ACCURACY = Gauge(
    "intent_accuracy",
    "Intent recognition accuracy rate",
)

# 工具调用次数
TOOL_CALLS_TOTAL = Counter(
    "tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "status"],
)

# RAG 命中次数
RAG_HITS_TOTAL = Counter(
    "rag_hits_total",
    "Total number of RAG hits",
    ["query_type"],
)

# 错误率
ERROR_TOTAL = Counter(
    "error_total",
    "Total number of errors",
    ["error_type", "endpoint"],
)

# ==================== 系统指标 ====================

# LLM 调用延迟
LLM_LATENCY_SECONDS = Histogram(
    "llm_latency_seconds",
    "LLM call latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# LLM Token 消耗
LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "token_type"],  # token_type: input/output
)

# Redis 延迟
REDIS_LATENCY_SECONDS = Histogram(
    "redis_latency_seconds",
    "Redis operation latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# 数据库延迟
DB_LATENCY_SECONDS = Histogram(
    "db_latency_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# 应用信息
APP_INFO = Info(
    "app",
    "Application information",
)

# 当前活跃会话数
ACTIVE_SESSIONS = Gauge(
    "active_sessions",
    "Number of active chat sessions",
)

# ==================== 辅助函数 ====================


def record_chat_request(
    session_id: str,
    intent: str,
    status: str,
    latency_seconds: float,
) -> None:
    """
    记录对话请求指标

    Args:
        session_id: 会话 ID
        intent: 意图类型
        status: 请求状态 (success/error)
        latency_seconds: 请求延迟（秒）
    """
    CHAT_REQUESTS_TOTAL.labels(
        session_id=session_id,
        intent=intent,
        status=status,
    ).inc()

    CHAT_LATENCY_SECONDS.labels(intent=intent).observe(latency_seconds)


def record_llm_call(
    model: str,
    latency_seconds: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """
    记录 LLM 调用指标

    Args:
        model: 模型名称
        latency_seconds: 调用延迟（秒）
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
    """
    LLM_LATENCY_SECONDS.labels(model=model).observe(latency_seconds)
    LLM_TOKENS_TOTAL.labels(model=model, token_type="input").inc(input_tokens)
    LLM_TOKENS_TOTAL.labels(model=model, token_type="output").inc(output_tokens)


def record_tool_call(tool_name: str, status: str = "success") -> None:
    """
    记录工具调用指标

    Args:
        tool_name: 工具名称
        status: 调用状态
    """
    TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status).inc()


def record_rag_hit(query_type: str = "default") -> None:
    """
    记录 RAG 命中指标

    Args:
        query_type: 查询类型
    """
    RAG_HITS_TOTAL.labels(query_type=query_type).inc()


def record_error(error_type: str, endpoint: str) -> None:
    """
    记录错误指标

    Args:
        error_type: 错误类型
        endpoint: 发生错误的端点
    """
    ERROR_TOTAL.labels(error_type=error_type, endpoint=endpoint).inc()


def record_redis_operation(operation: str, latency_seconds: float) -> None:
    """
    记录 Redis 操作指标

    Args:
        operation: 操作类型 (get/set/delete)
        latency_seconds: 操作延迟（秒）
    """
    REDIS_LATENCY_SECONDS.labels(operation=operation).observe(latency_seconds)


def record_db_operation(operation: str, latency_seconds: float) -> None:
    """
    记录数据库操作指标

    Args:
        operation: 操作类型 (select/insert/update/delete)
        latency_seconds: 操作延迟（秒）
    """
    DB_LATENCY_SECONDS.labels(operation=operation).observe(latency_seconds)


def set_app_info(version: str, environment: str) -> None:
    """
    设置应用信息

    Args:
        version: 应用版本
        environment: 运行环境
    """
    APP_INFO.info({"version": version, "environment": environment})


def set_active_sessions(count: int) -> None:
    """
    设置活跃会话数

    Args:
        count: 活跃会话数量
    """
    ACTIVE_SESSIONS.set(count)
