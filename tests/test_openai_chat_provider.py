from types import SimpleNamespace

import pytest

from agent.providers.openai_chat import OpenAIChatProvider
from agent.types import ChatMessage, ChatRequest, ModelToolCall


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeOpenAIClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=FakeCompletions(response))


def completion_response(message, finish_reason="stop", usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=usage,
    )


@pytest.mark.asyncio
async def test_openai_provider_sends_chat_completion_payload():
    client = FakeOpenAIClient(
        completion_response(SimpleNamespace(role="assistant", content="ok", tool_calls=None))
    )
    provider = OpenAIChatProvider(client=client)
    request = ChatRequest(
        model="gpt-test",
        messages=[
            ChatMessage(role="system", content="sys"),
            ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[ModelToolCall(id="call_1", name="search", arguments={"q": "python"})],
            ),
            ChatMessage(role="tool", content="result", tool_call_id="call_1", name="search"),
            ChatMessage(role="user", content="hello"),
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )

    response = await provider.chat_completion(request)

    payload = client.chat.completions.calls[0]
    assert payload["model"] == "gpt-test"
    assert payload["tools"] == request.tools
    assert payload["messages"][1]["tool_calls"][0]["function"]["arguments"] == '{"q": "python"}'
    assert payload["messages"][2] == {
        "role": "tool",
        "content": "result",
        "tool_call_id": "call_1",
    }
    assert response.message.content == "ok"


@pytest.mark.asyncio
async def test_openai_provider_parses_tool_calls_and_usage():
    openai_message = SimpleNamespace(
        role="assistant",
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="search", arguments='{"q": "python"}'),
            )
        ],
    )
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    client = FakeOpenAIClient(completion_response(openai_message, finish_reason="tool_calls", usage=usage))
    provider = OpenAIChatProvider(client=client)

    response = await provider.chat_completion(ChatRequest(model="gpt-test", messages=[]))

    assert response.finish_reason == "tool_calls"
    assert response.message.role == "assistant"
    assert response.tool_calls == [ModelToolCall(id="call_1", name="search", arguments={"q": "python"})]
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 5
    assert response.usage.total_tokens == 15
