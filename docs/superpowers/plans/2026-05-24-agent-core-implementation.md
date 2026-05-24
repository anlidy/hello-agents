# Agent Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simple, async, modular agent core with provider, tool, skill, context, runner, and conversation loop boundaries.

**Architecture:** Keep all first-version modules under `agent/` while splitting by lifecycle and responsibility. `ConversationLoop` orchestrates multi-turn sessions, `AgentRunner` owns one-turn ReAct execution, `ContextBuilder` assembles prompt messages, providers only call models, tools execute through a narrow context, and skills are prompt-only fragments.

**Tech Stack:** Python 3.12, dataclasses, typing Protocols, asyncio, `pytest`, and `pytest-asyncio`.

---

## File Structure

- Create `agent/types.py`: shared chat, tool-call, run-result, and streaming-compatible dataclasses.
- Create `agent/conversation/state.py`: long-lived `ConversationState`.
- Create `agent/conversation/policy.py`: async `ConversationPolicy` protocol and a simple default policy.
- Create `agent/runtime/state.py`: short-lived `RunState`, `IterationState`, and narrow `ToolExecutionContext`.
- Create `agent/providers/base.py`: async `LLMProvider` and optional `StreamingLLMProvider` protocols.
- Create `agent/providers/openai_chat.py`: OpenAI Chat Completions provider that converts internal chat contracts to and from SDK payloads.
- Create `agent/tools/base.py`: async `Tool` protocol and `ToolResult`.
- Create `agent/tools/registry.py`: registration, async schema loading, and normalized execution errors.
- Create `agent/skills/base.py`: prompt-only `Skill` protocol and static skill helper.
- Create `agent/skills/registry.py`: resolve ordered active skill prompts.
- Create `agent/context/messages.py`: message construction helpers.
- Create `agent/context/builder.py`: provider-ready message assembly.
- Replace `agent/runner.py`: async single-turn ReAct loop.
- Create `agent/loop.py`: async multi-turn conversation turn handler.
- Create `__init__.py` files for subpackages.
- Create tests under `tests/`.

## Tasks

Execution note: tests now use `pytest` with `pytest.mark.asyncio`.

### Task 1: Shared Contracts

**Files:**
- Create: `agent/types.py`
- Create: `tests/test_types_contracts.py`

- [ ] **Step 1: Write failing tests**

```python
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
    result = AgentRunResult(final_message=ChatMessage(role="assistant", content="done"), responses=[response])

    assert result.final_message.content == "done"
    assert result.responses == [response]
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_types_contracts.py -v`

Expected: FAIL because `agent.types` does not exist.

- [ ] **Step 3: Implement contracts**

Add dataclasses for `ChatMessage`, `ModelToolCall`, `Usage`, `ChatRequest`, `ChatResponse`, `ChatResponseChunk`, `ChatStreamEvent`, `AgentRunSpec`, and `AgentRunResult`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_types_contracts.py -v`

Expected: PASS.

### Task 2: Conversation And Runtime State

**Files:**
- Create: `agent/conversation/__init__.py`
- Create: `agent/conversation/state.py`
- Create: `agent/conversation/policy.py`
- Create: `agent/runtime/__init__.py`
- Create: `agent/runtime/state.py`
- Create: `tests/test_conversation_policy.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_conversation_policy.py` with `pytest.mark.asyncio` coverage for exit-command rejection and the narrow `ToolExecutionContext` contract.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_conversation_policy.py -v`

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement state and policy**

Implement long-lived `ConversationState`, async `ConversationPolicy` protocol, `DefaultConversationPolicy`, `RunState`, `IterationState`, and `ToolExecutionContext`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_conversation_policy.py -v`

Expected: PASS.

### Task 3: Tools, Skills, And Context

**Files:**
- Create: `agent/tools/__init__.py`
- Create: `agent/tools/base.py`
- Create: `agent/tools/registry.py`
- Create: `agent/skills/__init__.py`
- Create: `agent/skills/base.py`
- Create: `agent/skills/registry.py`
- Create: `agent/context/__init__.py`
- Create: `agent/context/messages.py`
- Create: `agent/context/builder.py`
- Create: `tests/test_tools_context.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_tools_context.py` with `pytest.mark.asyncio` coverage for async tool schemas, context-aware tool execution, normalized unknown-tool errors, and prompt/message ordering.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tools_context.py -v`

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement registries and context builder**

Implement async tool schema/execution, prompt-only skill registry, and message assembly helpers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tools_context.py -v`

Expected: PASS.

### Task 4: Provider Protocol, Runner, And Loop

**Files:**
- Create: `agent/providers/__init__.py`
- Create: `agent/providers/base.py`
- Create: `agent/providers/openai_chat.py`
- Replace: `agent/runner.py`
- Create: `agent/loop.py`
- Create: `tests/test_runner_loop.py`
- Create: `tests/test_openai_chat_provider.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_runner_loop.py` with `pytest.mark.asyncio` coverage for final-answer runs, ReAct tool execution, max-iteration stop behavior, single-turn persistence, and multi-turn loop orchestration.

Write `tests/test_openai_chat_provider.py` with fake OpenAI client coverage for Chat Completions payload conversion, assistant tool-call message payloads, tool result messages, parsed model tool calls, finish reasons, and usage.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_runner_loop.py tests/test_openai_chat_provider.py -v`

Expected: FAIL because provider, runner, loop, or OpenAI provider modules are incomplete.

- [ ] **Step 3: Implement provider protocols, runner, and loop**

Implement async provider protocols, `OpenAIChatProvider`, `AgentRunner.run(...)`, max iteration failure, and `ConversationLoop.handle_user_message(...)`.

- [ ] **Step 4: Run focused and full tests**

Run: `uv run pytest tests/test_runner_loop.py tests/test_openai_chat_provider.py -v`

Expected: PASS.

Run: `uv run pytest -v`

Expected: all tests PASS.

## Self-Review

- Spec coverage: async providers, async tool schema/execute, narrow tool context, policy separation, prompt-only skills, context builder, runner ReAct loop, and loop orchestration are covered.
- Placeholder scan: no implementation task depends on unspecified modules outside this plan.
- Type consistency: tests use the same class names and method signatures as the architecture document.
