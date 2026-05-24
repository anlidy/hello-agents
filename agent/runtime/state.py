from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agent.types import ChatMessage, ChatResponse


@dataclass(slots=True)
class IterationState:
    index: int
    response: ChatResponse | None = None
    tool_messages: list[ChatMessage] = field(default_factory=list)


@dataclass(slots=True)
class RunState:
    id: str = field(default_factory=lambda: str(uuid4()))
    messages: list[ChatMessage] = field(default_factory=list)
    iterations: list[IterationState] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolExecutionContext:
    run_id: str
    conversation_id: str | None
    user_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
