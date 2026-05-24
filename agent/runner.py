from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.context.builder import ContextBuilder
from agent.context.messages import tool_message
from agent.conversation.state import ConversationState
from agent.providers.base import LLMProvider
from agent.runtime.state import IterationState, RunState, ToolExecutionContext
from agent.tools.registry import ToolRegistry
from agent.types import AgentRunResult, ChatMessage, ChatRequest


@dataclass(slots=True)
class AgentRunner:
    provider: LLMProvider
    model: str
    context_builder: ContextBuilder = field(default_factory=ContextBuilder)
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    max_iterations: int = 8
    metadata: dict[str, Any] = field(default_factory=dict)

    async def run(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> AgentRunResult:
        run_state = RunState(metadata=dict[str, Any](self.metadata))
        responses = []

        for iteration_index in range(self.max_iterations):
            messages = await self.context_builder.build_messages(
                user_input,
                conversation,
                run_state.messages,
            )
            request = ChatRequest(
                model=self.model,
                messages=messages,
                tools=await self.tool_registry.schemas(),
                metadata={"run_id": run_state.id, **run_state.metadata},
            )
            response = await self.provider.chat_completion(request)
            responses.append(response)

            iteration = IterationState(index=iteration_index, response=response)
            run_state.iterations.append(iteration)

            if not response.tool_calls:
                return AgentRunResult(
                    final_message=response.message,
                    responses=responses,
                    success=True,
                    stop_reason=response.finish_reason or "stop",
                    metadata={"run_id": run_state.id},
                )

            assistant_message = response.message
            assistant_message.tool_calls = list(response.tool_calls)
            run_state.messages.append(assistant_message)
            context = ToolExecutionContext(
                run_id=run_state.id,
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                metadata=dict(conversation.metadata),
            )

            for tool_call in response.tool_calls:
                result = await self.tool_registry.execute(tool_call.name, tool_call.arguments, context)
                message = tool_message(result.content, tool_call.id, name=result.name)
                message.metadata["error"] = result.error
                iteration.tool_messages.append(message)
                run_state.messages.append(message)

        return AgentRunResult(
            final_message=ChatMessage(
                role="assistant",
                content="Agent stopped because max iterations were reached.",
            ),
            responses=responses,
            success=False,
            stop_reason="max_iterations",
            metadata={"run_id": run_state.id},
        )
