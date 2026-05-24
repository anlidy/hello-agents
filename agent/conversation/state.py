from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.types import ChatMessage


@dataclass(slots=True)
class ConversationState:
    id: str | None = None
    messages: list[ChatMessage] = field(default_factory=list)
    active_skill_names: list[str] = field(default_factory=list)
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
