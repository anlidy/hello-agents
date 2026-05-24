from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from agent.runtime.state import ToolExecutionContext
from agent.tools.base import Tool, ToolResult


@dataclass(slots=True)
class ToolRegistry:
    tools: Iterable[Tool] = field(default_factory=tuple)
    _tools_by_name: dict[str, Tool] = field(init=False)

    def __post_init__(self) -> None:
        self._tools_by_name = {tool.name: tool for tool in self.tools}

    def get(self, name: str) -> Tool | None:
        return self._tools_by_name.get(name)

    async def schemas(self) -> list[dict[str, Any]]:
        return [await tool.schema() for tool in self._tools_by_name.values()]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                name=name,
                content=f"Unknown tool requested: {name}",
                error="unknown_tool",
            )

        try:
            return await tool.execute(arguments, context)
        except Exception as exc:
            return ToolResult(
                name=name,
                content=f"Tool execution failed: {exc}",
                error="tool_execution_error",
                raw=exc,
            )
