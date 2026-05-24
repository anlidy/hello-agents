import pytest

from agent.conversation.policy import DefaultConversationPolicy
from agent.conversation.state import ConversationState
from agent.runtime.state import ToolExecutionContext


@pytest.mark.asyncio
async def test_default_policy_rejects_exit_commands():
    policy = DefaultConversationPolicy(exit_commands={"quit"})
    conversation = ConversationState(id="c1")

    assert await policy.accept_user_input("hello", conversation) is True
    assert await policy.accept_user_input(" quit ", conversation) is False


def test_tool_execution_context_is_narrow():
    context = ToolExecutionContext(
        run_id="r1",
        conversation_id="c1",
        user_id="u1",
        metadata={"role": "admin"},
    )

    assert context.run_id == "r1"
    assert not hasattr(context, "run")
