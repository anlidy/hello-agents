import pytest

from agent.context.builder import ContextBuilder
from agent.conversation.policy import DefaultConversationPolicy
from agent.conversation.state import ConversationState
from agent.loop import ConversationLoop
from agent.runner import AgentRunner
from agent.tools.base import ToolResult
from agent.tools.registry import ToolRegistry
from agent.types import ChatMessage, ChatResponse, ModelToolCall


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def chat_completion(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


class AddTool:
    name = "add"
    description = "Add numbers"

    async def schema(self):
        return {
            "type": "function",
            "function": {
                "name": "add",
                "description": self.description,
                "parameters": {"type": "object"},
            },
        }

    async def execute(self, arguments, context):
        return ToolResult(name="add", content=str(arguments["a"] + arguments["b"]))


@pytest.mark.asyncio
async def test_runner_returns_final_answer_without_tools():
    provider = FakeProvider(
        [ChatResponse(message=ChatMessage(role="assistant", content="hello"), finish_reason="stop")]
    )
    runner = AgentRunner(
        provider=provider,
        model="test",
        context_builder=ContextBuilder(),
        tool_registry=ToolRegistry(),
    )
    conversation = ConversationState(id="c1")

    result = await runner.run("hi", conversation)

    assert result.success is True
    assert result.final_message.content == "hello"
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_runner_executes_tool_and_sends_result_back_to_provider():
    provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage(role="assistant", content=None),
                tool_calls=[ModelToolCall(id="call_1", name="add", arguments={"a": 2, "b": 3})],
                finish_reason="tool_calls",
            ),
            ChatResponse(message=ChatMessage(role="assistant", content="5"), finish_reason="stop"),
        ]
    )
    runner = AgentRunner(
        provider=provider,
        model="test",
        context_builder=ContextBuilder(),
        tool_registry=ToolRegistry([AddTool()]),
    )
    conversation = ConversationState(id="c1", user_id="u1")

    result = await runner.run("2+3?", conversation)

    assert result.final_message.content == "5"
    assert len(provider.requests) == 2
    assert provider.requests[1].messages[-2].role == "assistant"
    assert provider.requests[1].messages[-2].tool_calls[0].id == "call_1"
    assert provider.requests[1].messages[-1].role == "tool"
    assert provider.requests[1].messages[-1].tool_call_id == "call_1"
    assert provider.requests[1].messages[-1].content == "5"


@pytest.mark.asyncio
async def test_runner_stops_at_max_iterations():
    provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage(role="assistant", content=None),
                tool_calls=[ModelToolCall(id="call_1", name="add", arguments={"a": 1, "b": 1})],
                finish_reason="tool_calls",
            )
        ]
    )
    runner = AgentRunner(
        provider=provider,
        model="test",
        context_builder=ContextBuilder(),
        tool_registry=ToolRegistry([AddTool()]),
        max_iterations=1,
    )

    result = await runner.run("loop", ConversationState(id="c1"))

    assert result.success is False
    assert result.stop_reason == "max_iterations"


@pytest.mark.asyncio
async def test_conversation_loop_delegates_policy_and_persists_messages():
    provider = FakeProvider(
        [ChatResponse(message=ChatMessage(role="assistant", content="ok"), finish_reason="stop")]
    )
    runner = AgentRunner(
        provider=provider,
        model="test",
        context_builder=ContextBuilder(),
        tool_registry=ToolRegistry(),
    )
    loop = ConversationLoop(runner=runner, policy=DefaultConversationPolicy())
    conversation = ConversationState(id="c1")

    result = await loop.handle_user_message("hi", conversation)

    assert result.final_message.content == "ok"
    assert [m.role for m in conversation.messages] == ["user", "assistant"]
    assert conversation.turn_count == 1


@pytest.mark.asyncio
async def test_conversation_loop_run_orchestrates_multiple_turns():
    provider = FakeProvider(
        [
            ChatResponse(message=ChatMessage(role="assistant", content="one"), finish_reason="stop"),
            ChatResponse(message=ChatMessage(role="assistant", content="two"), finish_reason="stop"),
        ]
    )
    runner = AgentRunner(
        provider=provider,
        model="test",
        context_builder=ContextBuilder(),
        tool_registry=ToolRegistry(),
    )
    loop = ConversationLoop(runner=runner, policy=DefaultConversationPolicy(max_turns=2))
    conversation = ConversationState(id="c1")
    inputs = iter(["first", "second", "third"])
    outputs = []

    async def receive():
        return next(inputs)

    async def respond(result):
        outputs.append(result.final_message.content)

    returned = await loop.run(conversation, receive, respond)

    assert returned is conversation
    assert outputs == ["one", "two"]
    assert conversation.turn_count == 2
