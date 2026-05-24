from __future__ import annotations

from dataclasses import dataclass, field

from agent.context.messages import system_message, user_message
from agent.conversation.state import ConversationState
from agent.skills.registry import SkillRegistry
from agent.types import ChatMessage


@dataclass(slots=True)
class ContextBuilder:
    base_system_prompt: str = "You are a helpful agent."
    skill_registry: SkillRegistry = field(default_factory=SkillRegistry)
    runtime_prompt: str | None = None

    async def build_messages(
        self,
        user_input: str,
        conversation: ConversationState,
        run_messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        messages = [system_message(self._system_prompt(conversation))]
        messages.extend(conversation.messages)
        messages.append(user_message(user_input))
        messages.extend(run_messages)
        return messages

    def _system_prompt(self, conversation: ConversationState) -> str:
        sections = [self.base_system_prompt]
        if self.runtime_prompt:
            sections.append(self.runtime_prompt)
        sections.extend(self.skill_registry.prompts_for(conversation.active_skill_names))
        return "\n\n".join(section for section in sections if section)
