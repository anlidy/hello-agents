from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent.runtime.state import ToolExecutionContext


@dataclass(slots=True)
class ToolResult:
    name: str
    content: str
    error: str | None = None
    raw: Any | None = None


class Tool(Protocol):
    name: str
    description: str

    async def schema(self) -> dict[str, Any]:
        ...

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        ...
