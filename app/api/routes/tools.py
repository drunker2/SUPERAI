"""
工具 API 路由
"""

from typing import Any

from fastapi import APIRouter

from app.tools import get_tool_registry
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tools", tags=["工具"])


@router.get(
    "/",
    summary="获取工具列表",
    description="""
返回所有已注册的工具及其参数定义。

## 可用工具
| 工具名 | 功能 |
|--------|------|
| calculate_bmi | 计算 BMI（身体质量指数） |
| calculate_bmr | 计算 BMR（基础代谢率） |
| calculate_body_fat | 估算体脂率 |
| generate_plan | 生成训练计划 |
| get_exercise_info | 查询动作详情 |
| list_exercises | 获取动作列表 |
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "count": 6,
                        "tools": [
                            {
                                "name": "calculate_bmi",
                                "description": "根据身高和体重计算 BMI",
                                "parameters": [
                                    {"name": "height", "type": "number", "description": "身高 (厘米)", "required": True},
                                    {"name": "weight", "type": "number", "description": "体重 (公斤)", "required": True},
                                ]
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def list_tools() -> dict[str, Any]:
    """
    获取工具列表

    返回所有已注册工具的名称、描述和参数定义。
    用于了解系统支持的工具类型和参数要求。
    """
    registry = get_tool_registry()
    tools = registry.get_tool_docs()

    return {
        "count": len(tools),
        "tools": tools,
    }


@router.get(
    "/{tool_name}",
    summary="获取工具详情",
    description="""
返回指定工具的详细信息，包括参数定义和 OpenAI 格式 Schema。

## 返回内容
- 工具名称、描述、版本
- 参数定义：名称、类型、是否必填、取值范围等
- OpenAI Function Calling 格式的 Schema
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "name": "calculate_bmi",
                        "description": "根据身高和体重计算 BMI (身体质量指数)",
                        "version": "1.0.0",
                        "parameters": [
                            {"name": "height", "type": "number", "description": "身高 (厘米)", "required": True, "minimum": 50, "maximum": 300},
                            {"name": "weight", "type": "number", "description": "体重 (公斤)", "required": True, "minimum": 20, "maximum": 500},
                        ],
                        "openai_schema": {
                            "type": "function",
                            "function": {
                                "name": "calculate_bmi",
                                "description": "根据身高和体重计算 BMI",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "height": {"type": "number", "description": "身高 (厘米)"},
                                        "weight": {"type": "number", "description": "体重 (公斤)"},
                                    },
                                    "required": ["height", "weight"],
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "工具不存在",
            "content": {
                "application/json": {
                    "example": {
                        "error": "工具不存在: unknown_tool",
                        "available_tools": ["calculate_bmi", "calculate_bmr", "calculate_body_fat"]
                    }
                }
            }
        },
    },
)
async def get_tool_detail(tool_name: str) -> dict[str, Any]:
    """
    获取工具详情

    - **tool_name**: 工具名称（路径参数）

    返回工具的完整定义，包括参数和 OpenAI 格式 Schema
    """
    registry = get_tool_registry()
    tool = registry.get(tool_name)

    if tool is None:
        return {
            "error": f"工具不存在: {tool_name}",
            "available_tools": registry.list_names(),
        }

    return {
        "name": tool.name,
        "description": tool.description,
        "version": tool.version,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default": p.default,
                "enum": p.enum,
                "minimum": p.minimum,
                "maximum": p.maximum,
            }
            for p in tool.parameters
        ],
        "openai_schema": tool.to_openai_tool(),
    }


@router.get(
    "/openai/format",
    summary="获取 OpenAI 格式工具定义",
    description="""
返回 OpenAI Function Calling 格式的工具定义。

## 用途
用于与 OpenAI API 兼容的 Function Calling 场景，可以直接传递给支持 OpenAI 格式的 LLM。

## 格式说明
返回的工具定义遵循 OpenAI Function Calling 规范：
```json
{
  "type": "function",
  "function": {
    "name": "工具名称",
    "description": "工具描述",
    "parameters": {
      "type": "object",
      "properties": {...},
      "required": [...]
    }
  }
}
```
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "count": 6,
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "calculate_bmi",
                                    "description": "根据身高和体重计算 BMI",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "height": {"type": "number", "description": "身高 (厘米)"},
                                            "weight": {"type": "number", "description": "体重 (公斤)"},
                                        },
                                        "required": ["height", "weight"],
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        },
    },
)
async def get_openai_tools() -> dict[str, Any]:
    """
    获取 OpenAI 格式工具定义

    用于与 OpenAI API 兼容的 Function Calling。
    可直接传递给支持 OpenAI 格式的 LLM 进行工具调用。
    """
    registry = get_tool_registry()
    tools = registry.to_openai_tools()

    return {
        "count": len(tools),
        "tools": tools,
    }
