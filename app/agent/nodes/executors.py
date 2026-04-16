"""
执行节点

包含知识检索、工具执行、MCP 服务执行等节点
"""

import asyncio
import time
from typing import Any

from app.agent.state import AgentState
from app.tools import get_tool_registry, ToolResult
from app.rag import get_indexer
from app.utils import get_logger, bind_context

logger = get_logger(__name__)

# 意图到工具的映射
INTENT_TOOL_MAP: dict[str, str] = {
    "body_metrics": "calculate_bmi",  # 身体指标计算 -> BMI 工具
    "plan_request": "generate_plan",  # 训练计划请求 -> 计划生成工具
    "exercise_guide": "get_exercise_info",  # 动作指导 -> 动作信息工具
}


def extract_tool_params(query: str, intent: str, entities: dict[str, Any] | None) -> dict[str, Any]:
    """
    从查询和实体中提取工具参数

    Args:
        query: 用户查询
        intent: 意图类型
        entities: 提取的实体

    Returns:
        工具参数字典
    """
    params: dict[str, Any] = {}

    if not entities:
        return params

    # BMI 工具参数提取
    if intent == "body_metrics":
        # 身高
        if "height" in entities:
            params["height"] = entities["height"]
        elif "身高" in entities:
            params["height"] = entities["身高"]

        # 体重
        if "weight" in entities:
            params["weight"] = entities["weight"]
        elif "体重" in entities:
            params["weight"] = entities["体重"]

        # 年龄和性别 (用于 BMR)
        if "age" in entities or "年龄" in entities:
            params["age"] = entities.get("age") or entities.get("年龄")
        if "gender" in entities or "性别" in entities:
            params["gender"] = entities.get("gender") or entities.get("性别")

    # 计划生成参数提取
    if intent == "plan_request":
        # 目标
        goal_map = {
            "减脂": "减脂", "减重": "减脂", "减肥": "减脂", "瘦身": "减脂",
            "增肌": "增肌", "增重": "增肌", "增壮": "增肌",
            "塑形": "塑形", "线条": "塑形", "雕刻": "塑形",
        }
        if "goal" in entities or "目标" in entities:
            goal = entities.get("goal") or entities.get("目标")
            params["goal"] = goal_map.get(goal, goal)

        # 水平
        level_map = {
            "初级": "初级", "新手": "初级", "入门": "初级", "小白": "初级", "初学": "初级",
            "中级": "中级", "进阶": "中级", "有一定基础": "中级",
            "高级": "高级", "高手": "高级", "老手": "高级", "资深": "高级",
        }
        if "level" in entities or "水平" in entities:
            level = entities.get("level") or entities.get("水平")
            params["level"] = level_map.get(level, level)
        else:
            # 默认初级
            params["level"] = "初级"

        # 频率
        if "frequency" in entities or "频率" in entities:
            params["frequency"] = entities.get("frequency") or entities.get("频率")
        else:
            # 默认 3 天
            params["frequency"] = 3

    # 动作指导参数提取
    if intent == "exercise_guide":
        if "exercise_name" in entities or "动作" in entities or "练习" in entities:
            params["exercise_name"] = (
                entities.get("exercise_name")
                or entities.get("动作")
                or entities.get("练习")
            )

    return params


def retriever_node(state: AgentState) -> AgentState:
    """
    知识检索节点

    使用向量检索从知识库中获取相关文档
    """
    query = state["query"]
    session_id = state["session_id"]

    bind_context(node="retriever", session_id=session_id)

    start_time = time.perf_counter()
    logger.info("知识检索开始", query=query[:50])

    try:
        # 获取索引器
        indexer = get_indexer()

        # 检查是否有文档
        if indexer.count() == 0:
            logger.warning("知识库为空，跳过检索")
            state["retrieved_docs"] = []
            return state

        # 执行检索
        results = indexer.search(query, n_results=3)

        # 过滤低相关性结果
        relevance_threshold = 0.5
        filtered_results = [
            r for r in results
            if r.get("distance", 0) < relevance_threshold or r.get("distance", 0) > 0.5
        ]

        # 格式化结果
        retrieved_docs = []
        for r in filtered_results:
            retrieved_docs.append({
                "content": r.get("content", ""),
                "source": r.get("metadata", {}).get("source", "未知"),
                "score": r.get("distance", 0),
            })

        state["retrieved_docs"] = retrieved_docs

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "知识检索完成",
            results_count=len(retrieved_docs),
            duration_ms=round(duration_ms, 2),
        )

        return state

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "知识检索失败",
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )
        state["retrieved_docs"] = []
        state["errors"] = state.get("errors", []) + [f"知识检索失败: {e}"]
        return state


async def tool_executor_node(state: AgentState) -> AgentState:
    """
    工具执行节点

    根据意图选择并执行相应工具，将结果写入 state
    """
    import time

    query = state["query"]
    session_id = state["session_id"]
    intent = state.get("intent", "unknown")
    entities = state.get("entities")

    bind_context(node="tool_executor", session_id=session_id)

    start_time = time.perf_counter()
    logger.info("工具执行开始", intent=intent, query=query[:50])

    try:
        registry = get_tool_registry()

        # 根据意图选择工具
        tool_name = INTENT_TOOL_MAP.get(intent)

        if not tool_name:
            logger.warning("没有对应的工具", intent=intent)
            state["tool_results"] = []
            return state

        # 检查工具是否存在
        if not registry.exists(tool_name):
            logger.warning("工具未注册", tool_name=tool_name)
            state["tool_results"] = []
            return state

        # 提取参数
        params = extract_tool_params(query, intent, entities)
        logger.info("提取的工具参数", params=params)

        # 执行工具
        result: ToolResult = await registry.execute(tool_name, **params)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # 记录工具调用
        tool_call = {
            "tool_name": tool_name,
            "params": params,
            "status": result.status.value,
            "duration_ms": round(duration_ms, 2),
        }

        # 更新状态
        state["tool_calls"] = state.get("tool_calls", []) + [tool_call]

        if result.is_success:
            state["tool_results"] = state.get("tool_results", []) + [result.to_dict()]
            logger.info(
                "工具执行成功",
                tool_name=tool_name,
                duration_ms=round(duration_ms, 2),
            )
        else:
            logger.warning(
                "工具执行失败",
                tool_name=tool_name,
                error=result.error,
            )
            state["errors"] = state.get("errors", []) + [f"工具 {tool_name} 执行失败: {result.error}"]

        return state

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "工具执行异常",
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )
        state["errors"] = state.get("errors", []) + [f"工具执行异常: {e}"]
        state["tool_results"] = state.get("tool_results", []) + [
            {"error": str(e), "status": "error"}
        ]
        return state


async def mcp_executor_node(state: AgentState) -> AgentState:
    """
    MCP 服务执行节点

    根据意图调用 MCP 服务获取动作信息等
    """
    query = state["query"]
    session_id = state["session_id"]
    intent = state.get("intent", "unknown")
    entities = state.get("entities")

    bind_context(node="mcp_executor", session_id=session_id)

    start_time = time.perf_counter()
    logger.info("MCP 执行开始", intent=intent, query=query[:50])

    try:
        from app.mcp.tools import get_exercise_info_sync, search_exercises_sync

        mcp_results = []

        # 根据意图调用不同的 MCP 服务
        if intent == "exercise_guide":
            # 动作指导 - 查询动作详情
            exercise_name = None
            if entities:
                exercise_name = (
                    entities.get("exercise_name")
                    or entities.get("动作")
                    or entities.get("练习")
                )

            if exercise_name:
                result = get_exercise_info_sync(exercise_name)
                mcp_results.append({
                    "type": "exercise_info",
                    "query": exercise_name,
                    "result": result,
                })

        elif intent == "fitness_consult":
            # 健身咨询 - 搜索相关动作
            # 从查询中提取可能的身体部位关键词
            body_parts = ["腿", "胸", "背", "肩", "手臂", "腹肌", "核心"]
            category_map = {
                "腿": "腿部", "腿部": "腿部",
                "胸": "胸部", "胸部": "胸部",
                "背": "背部", "背部": "背部",
                "肩": "肩部", "肩部": "肩部",
                "手臂": "手臂",
                "腹肌": "核心", "核心": "核心",
            }

            for part in body_parts:
                if part in query:
                    category = category_map.get(part)
                    if category:
                        result = search_exercises_sync(category=category)
                        mcp_results.append({
                            "type": "exercise_search",
                            "category": category,
                            "result": result,
                        })
                    break

        state["mcp_results"] = mcp_results

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "MCP 执行完成",
            results_count=len(mcp_results),
            duration_ms=round(duration_ms, 2),
        )

        return state

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "MCP 执行失败",
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )
        state["mcp_results"] = []
        state["errors"] = state.get("errors", []) + [f"MCP 服务执行失败: {e}"]
        return state
