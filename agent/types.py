from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class ChatMessage:
    role: ChatRole
    content: str | None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ModelToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModelToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChatResponse:
    message: ChatMessage
    tool_calls: list[ModelToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage | None = None
    raw: Any | None = None


@dataclass(slots=True)
class ChatResponseChunk:
    delta: ChatMessage | None = None
    tool_calls: list[ModelToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    raw: Any | None = None


@dataclass(slots=True)
class ChatStreamEvent:
    type: str
    chunk: ChatResponseChunk | None = None
    error: str | None = None


@dataclass(slots=True)
class AgentRunSpec:
    model: str
    max_iterations: int = 8
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentRunResult:
    final_message: ChatMessage
    responses: list[ChatResponse] = field(default_factory=list)
    success: bool = True
    stop_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)
