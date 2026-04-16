"""
工具注册器

提供全局工具注册和发现功能
"""

from typing import Any, Type

from app.tools.base import BaseTool, ToolResult
from app.utils import get_logger
from app.utils.metrics import record_tool_call

logger = get_logger(__name__)


class ToolRegistry:
    """
    工具注册器

    管理所有已注册的工具，支持:
    - 全局注册
    - 按名称/类型发现
    - 工具验证
    - 文档生成
    """

    def __init__(self):
        """初始化注册器"""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        注册工具

        Args:
            tool: 工具实例

        Raises:
            ValueError: 工具已存在
        """
        if tool.name in self._tools:
            raise ValueError(f"工具已存在: {tool.name}")

        self._tools[tool.name] = tool
        logger.info("工具已注册", tool_name=tool.name)

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("工具已注销", tool_name=name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            工具实例，不存在返回 None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """
        获取所有工具

        Returns:
            工具列表
        """
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """
        获取所有工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def exists(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            是否存在
        """
        return name in self._tools

    def count(self) -> int:
        """
        获取工具数量

        Returns:
            工具数量
        """
        return len(self._tools)

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果

        Raises:
            ToolError: 工具不存在或执行失败
        """
        tool = self.get(name)
        if tool is None:
            from app.tools.base import ToolError
            raise ToolError(f"工具不存在: {name}", tool_name=name)

        # 验证参数
        validated_params = tool.validate_parameters(kwargs)

        # 执行工具
        logger.info(
            "工具执行开始",
            tool_name=name,
            params=validated_params,
        )

        try:
            result = await tool.execute(**validated_params)

            logger.info(
                "工具执行完成",
                tool_name=name,
                status=result.status.value,
                is_success=result.is_success,
            )

            # 记录 Prometheus 指标
            record_tool_call(tool_name=name, status="success" if result.is_success else "error")

            return result

        except Exception as e:
            from app.tools.base import ToolResult, ToolStatus
            logger.error("工具执行失败", tool_name=name, error=str(e))
            # 记录 Prometheus 指标
            record_tool_call(tool_name=name, status="error")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """
        转换为 OpenAI 工具列表

        Returns:
            OpenAI 工具定义列表
        """
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def to_langchain_tools(self) -> list[dict[str, Any]]:
        """
        转换为 LangChain 工具列表

        Returns:
            LangChain 工具定义列表
        """
        return [tool.to_langchain_tool() for tool in self._tools.values()]

    def get_tool_docs(self) -> list[dict[str, Any]]:
        """
        获取工具文档

        Returns:
            工具文档列表
        """
        docs = []
        for tool in self._tools.values():
            docs.append({
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
                    }
                    for p in tool.parameters
                ],
            })
        return docs


# 全局注册器实例
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册器

    Returns:
        ToolRegistry 实例
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: BaseTool) -> None:
    """
    注册工具到全局注册器

    Args:
        tool: 工具实例
    """
    registry = get_tool_registry()
    registry.register(tool)


def tool_decorator(name: str | None = None, description: str | None = None):
    """
    工具装饰器

    Usage:
        @tool_decorator()
        async def my_tool(x: int) -> str:
            '''工具描述'''
            return str(x)
    """
    def decorator(func):
        from app.tools.base import BaseTool, ToolResult
        import asyncio

        class DecoratedTool(BaseTool):
            _name = name or func.__name__
            _description = description or func.__doc__ or f"工具: {func.__name__}"

            @property
            def name(self) -> str:
                return self._name

            @property
            def description(self) -> str:
                return self._description

            async def execute(self, **kwargs: Any) -> ToolResult:
                try:
                    # 支持同步和异步函数
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**kwargs)
                    else:
                        result = func(**kwargs)
                    return ToolResult.success(result)
                except Exception as e:
                    return ToolResult.error(str(e))

        # 注册工具
        tool_instance = DecoratedTool()
        register_tool(tool_instance)

        return func

    return decorator
