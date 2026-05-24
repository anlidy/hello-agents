from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent.types import ChatMessage, ChatRequest, ChatResponse, ModelToolCall, Usage


@dataclass(slots=True)
class OpenAIChatProvider:
    client: Any | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI()

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [self._message_to_payload(message) for message in request.messages],
        }
        if request.tools:
            payload["tools"] = request.tools

        response = await self.client.chat.completions.create(**payload)
        choice = response.choices[0]
        message = choice.message
        tool_calls = self._parse_tool_calls(getattr(message, "tool_calls", None))

        return ChatResponse(
            message=ChatMessage(
                role=getattr(message, "role", "assistant"),
                content=getattr(message, "content", None),
                tool_calls=tool_calls,
            ),
            tool_calls=tool_calls,
            finish_reason=getattr(choice, "finish_reason", None),
            usage=self._parse_usage(getattr(response, "usage", None)),
            raw=response,
        )

    def _message_to_payload(self, message: ChatMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.name and message.role != "tool":
            payload["name"] = message.name
        if message.role == "tool":
            payload["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            payload["tool_calls"] = [self._tool_call_to_payload(tool_call) for tool_call in message.tool_calls]
        return {key: value for key, value in payload.items() if value is not None}

    def _tool_call_to_payload(self, tool_call: ModelToolCall) -> dict[str, Any]:
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.name,
                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
            },
        }

    def _parse_tool_calls(self, tool_calls: Any) -> list[ModelToolCall]:
        if not tool_calls:
            return []

        parsed: list[ModelToolCall] = []
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            arguments = getattr(function, "arguments", "{}")
            parsed.append(
                ModelToolCall(
                    id=getattr(tool_call, "id"),
                    name=getattr(function, "name"),
                    arguments=json.loads(arguments or "{}"),
                )
            )
        return parsed

    def _parse_usage(self, usage: Any) -> Usage | None:
        if usage is None:
            return None
        return Usage(
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
