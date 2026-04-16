"""
MCP 客户端

用于连接和调用 MCP 服务
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    MCP 客户端

    支持连接 MCP 服务并调用工具
    """

    def __init__(
        self,
        server_command: str = "python",
        server_args: list[str] | None = None,
        timeout: float = 10.0,
    ):
        """
        初始化 MCP 客户端

        Args:
            server_command: 服务启动命令
            server_args: 服务启动参数
            timeout: 调用超时时间(秒)
        """
        self.server_command = server_command
        self.server_args = server_args or ["-m", "app.mcp.server"]
        self.timeout = timeout
        self._session: ClientSession | None = None
        self._tools_cache: list[dict] | None = None

    @asynccontextmanager
    async def connect(self):
        """
        连接到 MCP 服务

        Usage:
            async with client.connect() as session:
                result = await client.call_tool("get_exercise_info", {...})
        """
        server_params = StdioServerParameters(
            command=self.server_command,
            args=self.server_args,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化连接
                await session.initialize()
                self._session = session
                logger.info("MCP 客户端已连接")
                yield self

    async def list_tools(self) -> list[dict]:
        """
        获取可用工具列表

        Returns:
            工具列表
        """
        if self._session is None:
            raise RuntimeError("未连接到 MCP 服务")

        if self._tools_cache is not None:
            return self._tools_cache

        tools = await self._session.list_tools()
        self._tools_cache = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools.tools
        ]

        return self._tools_cache

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        调用 MCP 工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果
        """
        if self._session is None:
            raise RuntimeError("未连接到 MCP 服务")

        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments or {}),
                timeout=self.timeout,
            )

            duration_ms = (time.perf_counter() - start) * 1000

            # 解析结果
            content = result.content
            if content and len(content) > 0:
                text = content[0].text
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {"result": text}
            else:
                data = {}

            logger.info(
                "MCP 工具调用完成",
                tool=name,
                duration_ms=round(duration_ms, 2),
            )

            return data

        except asyncio.TimeoutError:
            logger.warning("MCP 工具调用超时", tool=name, timeout=self.timeout)
            return {"error": f"调用超时 ({self.timeout}s)"}

        except Exception as e:
            logger.error("MCP 工具调用失败", tool=name, error=str(e))
            return {"error": str(e)}

    async def get_exercise_info(self, exercise_name: str) -> dict[str, Any]:
        """
        查询动作信息

        Args:
            exercise_name: 动作名称

        Returns:
            动作详情
        """
        return await self.call_tool("get_exercise_info", {"exercise_name": exercise_name})

    async def search_exercises(
        self,
        query: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
    ) -> dict[str, Any]:
        """
        搜索动作

        Args:
            query: 搜索关键词
            category: 分类
            difficulty: 难度

        Returns:
            搜索结果
        """
        args = {}
        if query:
            args["query"] = query
        if category:
            args["category"] = category
        if difficulty:
            args["difficulty"] = difficulty

        return await self.call_tool("search_exercises", args)


class MCPServicePool:
    """
    MCP 服务连接池

    管理多个 MCP 服务连接
    """

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    def get_client(self, service_name: str = "exercise") -> MCPClient:
        """
        获取 MCP 客户端

        Args:
            service_name: 服务名称

        Returns:
            MCP 客户端实例
        """
        if service_name not in self._clients:
            self._clients[service_name] = MCPClient()
        return self._clients[service_name]

    async def call_tool(
        self,
        service_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        调用 MCP 工具

        Args:
            service_name: 服务名称
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果
        """
        client = self.get_client(service_name)

        async with client.connect():
            return await client.call_tool(tool_name, arguments)


# 全局服务池
_pool: MCPServicePool | None = None


def get_mcp_client() -> MCPServicePool:
    """获取 MCP 客户端池"""
    global _pool
    if _pool is None:
        _pool = MCPServicePool()
    return _pool
