from __future__ import annotations

from agent.types import ChatMessage


def system_message(content: str) -> ChatMessage:
    return ChatMessage(role="system", content=content)


def user_message(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


def assistant_message(content: str | None) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def tool_message(content: str, tool_call_id: str, name: str | None = None) -> ChatMessage:
    return ChatMessage(role="tool", content=content, name=name, tool_call_id=tool_call_id)
