from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent.conversation.state import ConversationState


class ConversationPolicy(Protocol):
    async def should_continue(self, conversation: ConversationState) -> bool:
        ...

    async def accept_user_input(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> bool:
        ...


@dataclass(slots=True)
class DefaultConversationPolicy:
    exit_commands: set[str] = field(default_factory=lambda: {"exit", "quit"})
    max_turns: int | None = None

    async def should_continue(self, conversation: ConversationState) -> bool:
        if self.max_turns is None:
            return True
        return conversation.turn_count < self.max_turns

    async def accept_user_input(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> bool:
        del conversation
        return user_input.strip().lower() not in self.exit_commands
