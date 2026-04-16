"""
工具基类定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict


class ToolStatus(str, Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """
    工具执行结果

    统一的工具返回格式，支持成功和错误状态
    """
    status: ToolStatus
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == ToolStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {
            "status": self.status.value,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def success(cls, data: Any, metadata: dict[str, Any] | None = None) -> "ToolResult":
        """创建成功结果"""
        return cls(
            status=ToolStatus.SUCCESS,
            data=data,
            metadata=metadata or {},
        )

    @classmethod
    def error(cls, error: str, metadata: dict[str, Any] | None = None) -> "ToolResult":
        """创建错误结果"""
        return cls(
            status=ToolStatus.ERROR,
            error=error,
            metadata=metadata or {},
        )


class ToolError(Exception):
    """工具执行异常"""

    def __init__(self, message: str, tool_name: str | None = None):
        self.message = message
        self.tool_name = tool_name
        super().__init__(message)


class ToolParameterSchema(BaseModel):
    """工具参数 Schema"""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None

    def to_openapi(self) -> dict[str, Any]:
        """转换为 OpenAPI Schema"""
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.default is not None:
            schema["default"] = self.default
        return schema


class BaseTool(ABC):
    """
    工具基类

    所有工具必须继承此类并实现 execute 方法
    """

    # 工具元信息
    name: str
    description: str
    version: str = "1.0.0"

    # 参数 Schema
    parameters: list[ToolParameterSchema] = []

    # 执行配置
    timeout: float = 30.0  # 超时时间(秒)

    def __init__(self):
        """初始化工具"""
        self._validate_tool_definition()

    def _validate_tool_definition(self) -> None:
        """验证工具定义是否完整"""
        if not hasattr(self, 'name') or not self.name:
            raise ValueError("工具必须定义 name 属性")
        if not hasattr(self, 'description') or not self.description:
            raise ValueError("工具必须定义 description 属性")

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def validate_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        验证并填充参数

        Args:
            params: 输入参数

        Returns:
            验证后的参数

        Raises:
            ToolError: 参数验证失败
        """
        validated = {}

        # 检查必填参数
        param_map = {p.name: p for p in self.parameters}

        for param in self.parameters:
            value = params.get(param.name)

            # 必填检查
            if param.required and value is None and param.default is None:
                raise ToolError(
                    f"缺少必填参数: {param.name}",
                    tool_name=self.name,
                )

            # 使用默认值
            if value is None and param.default is not None:
                value = param.default

            # 类型检查和转换
            if value is not None:
                try:
                    value = self._convert_type(value, param.type)
                except (ValueError, TypeError) as e:
                    raise ToolError(
                        f"参数类型错误 {param.name}: {e}",
                        tool_name=self.name,
                    )

                # 边界检查
                if param.minimum is not None and isinstance(value, (int, float)):
                    if value < param.minimum:
                        raise ToolError(
                            f"参数 {param.name} 值 {value} 小于最小值 {param.minimum}",
                            tool_name=self.name,
                        )
                if param.maximum is not None and isinstance(value, (int, float)):
                    if value > param.maximum:
                        raise ToolError(
                            f"参数 {param.name} 值 {value} 大于最大值 {param.maximum}",
                            tool_name=self.name,
                        )
                if param.enum and value not in param.enum:
                    raise ToolError(
                        f"参数 {param.name} 值 {value} 不在允许列表 {param.enum} 中",
                        tool_name=self.name,
                    )

            validated[param.name] = value

        return validated

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """类型转换"""
        if target_type == "string":
            return str(value)
        elif target_type == "integer":
            return int(value)
        elif target_type == "number":
            return float(value)
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif target_type == "array":
            if isinstance(value, list):
                return value
            raise ValueError(f"无法将 {type(value)} 转换为 array")
        elif target_type == "object":
            if isinstance(value, dict):
                return value
            raise ValueError(f"无法将 {type(value)} 转换为 object")
        return value

    def to_openai_tool(self) -> dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式

        Returns:
            OpenAI 工具定义
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_openapi()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_langchain_tool(self) -> dict[str, Any]:
        """
        转换为 LangChain 工具格式

        Returns:
            LangChain 工具定义
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.to_openai_tool()["function"]["parameters"],
        }

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"


# 同步工具包装器
def sync_tool(func: Callable[..., Any]) -> type[BaseTool]:
    """
    将同步函数包装为工具类

    Usage:
        @sync_tool
        def my_tool(x: int) -> str:
            return str(x)
    """
    class SyncToolWrapper(BaseTool):
        name = func.__name__
        description = func.__doc__ or f"工具: {func.__name__}"
        parameters = []
        _func = func

        async def execute(self, **kwargs: Any) -> ToolResult:
            try:
                result = self._func(**kwargs)
                return ToolResult.success(result)
            except Exception as e:
                return ToolResult.error(str(e))

    return SyncToolWrapper
