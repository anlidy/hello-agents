from agent.types import AgentRunResult, ChatMessage, ChatResponse, ModelToolCall


def test_chat_message_preserves_role_content_and_metadata():
    message = ChatMessage(role="user", content="hello", name="alice", metadata={"k": "v"})

    assert message.role == "user"
    assert message.content == "hello"
    assert message.name == "alice"
    assert message.metadata == {"k": "v"}


def test_run_result_exposes_final_message_and_iterations():
    response = ChatResponse(
        message=ChatMessage(role="assistant", content="done"),
        tool_calls=[ModelToolCall(id="call_1", name="search", arguments={"q": "x"})],
        finish_reason="tool_calls",
    )
    result = AgentRunResult(
        final_message=ChatMessage(role="assistant", content="done"),
        responses=[response],
    )

    assert result.final_message.content == "done"
    assert result.responses == [response]
    assert result.success is True
