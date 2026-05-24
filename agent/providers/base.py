from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from agent.types import ChatRequest, ChatResponse, ChatStreamEvent


class LLMProvider(Protocol):
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        ...


class StreamingLLMProvider(LLMProvider, Protocol):
    async def stream_chat_completion(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatStreamEvent]:
        ...
