from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from agent.context.messages import user_message
from agent.conversation.policy import ConversationPolicy, DefaultConversationPolicy
from agent.conversation.state import ConversationState
from agent.runner import AgentRunner
from agent.types import AgentRunResult


@dataclass(slots=True)
class ConversationLoop:
    runner: AgentRunner
    policy: ConversationPolicy = field(default_factory=DefaultConversationPolicy)

    async def run(
        self,
        conversation: ConversationState,
        receive_user_input: Callable[[], Awaitable[str | None]],
        respond: Callable[[AgentRunResult], Awaitable[None]],
    ) -> ConversationState:
        while await self.policy.should_continue(conversation):
            user_input = await receive_user_input()
            if user_input is None:
                break

            result = await self.handle_user_message(user_input, conversation)
            if result.stop_reason == "user_input_rejected":
                break

            await respond(result)

        return conversation

    async def handle_user_message(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> AgentRunResult:
        if not await self.policy.should_continue(conversation):
            return self._rejected("conversation_policy_stop")

        if not await self.policy.accept_user_input(user_input, conversation):
            return self._rejected("user_input_rejected")

        result = await self.runner.run(user_input, conversation)
        conversation.messages.append(user_message(user_input))
        conversation.messages.append(result.final_message)
        conversation.turn_count += 1
        return result

    def _rejected(self, reason: str) -> AgentRunResult:
        from agent.types import ChatMessage

        return AgentRunResult(
            final_message=ChatMessage(role="assistant", content=None),
            responses=[],
            success=False,
            stop_reason=reason,
        )
