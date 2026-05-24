# Agent Core Architecture Design

Date: 2026-05-24

## Goal

Build a simple, extensible agent core for `hello-agents`.

The first implementation should support Chat Completions style providers, a ReAct-style tool reasoning loop, multi-turn conversation orchestration, skills, tools, and prompt context assembly without placing all logic in one file.

## Design Principles

- Keep the initial package small and easy to change.
- Put agent core modules under the `agent` package first.
- Separate responsibilities by runtime boundary, not by implementation convenience.
- Make providers, tools, and skills extensible through protocols and registries.
- Avoid early extraction into top-level packages until public APIs stabilize.
- Keep provider implementations focused on model requests only.

## Package Layout

Initial layout:

```text
agent/
  __init__.py
  loop.py
  runner.py
  state.py
  types.py
  providers/
    __init__.py
    base.py
  tools/
    __init__.py
    base.py
    registry.py
  skills/
    __init__.py
    base.py
    registry.py
  context/
    __init__.py
    builder.py
    messages.py
```

This keeps related code together while preserving clear internal boundaries. Later, when the interfaces are stable, these subpackages can be moved into separately distributed packages such as `hello_agents_providers`, `hello_agents_tools`, or `hello_agents_skills`.

## Responsibility Boundaries

### `loop.py`

`loop` owns multi-turn conversation orchestration.

It handles the outer conversation lifecycle:

- Receive or accept each user input.
- Load the current conversation/session state.
- Call `AgentRunner.run(...)` for one user turn.
- Persist the final assistant response and any updated session state.
- Decide whether the conversation continues.
- Provide a natural integration point for CLI, API, WebSocket, or UI frontends.

`loop` does not execute tools directly and does not implement the ReAct loop.

Conceptually:

```text
while conversation_active:
  user_input = receive()
  result = runner.run(user_input, session_context)
  session_context = persist(result)
  respond(result.final_message)
```

### `runner.py`

`runner` owns one agent run for a single user turn.

It handles the internal ReAct-style model/tool reasoning loop:

- Build model-ready context for the current run.
- Request the provider.
- Inspect the model response.
- Execute requested tool calls through `ToolRegistry`.
- Append tool results to the run messages.
- Continue until final answer, max iterations, or unrecoverable failure.
- Return an `AgentRunResult` to the conversation loop.

Conceptually:

```text
user input
  -> model response
  -> tool call
  -> tool result
  -> model response
  -> final assistant answer
```

This whole inner sequence is one `AgentRunner.run(...)`.

### `providers`

`providers` owns model transport.

The provider layer should not know about the conversation loop, skills registry internals, or tool execution policy. It accepts a normalized chat request and returns a normalized chat response.

Initial target: Chat Completions style request/response.

Expected responsibilities:

- Convert internal `ChatRequest` into provider-specific API payloads.
- Send the request.
- Convert provider-specific responses into internal `ChatResponse`.
- Normalize tool calls, finish reasons, usage, and errors.

Non-responsibilities:

- No ReAct loop.
- No direct tool execution.
- No session persistence.
- No prompt policy decisions beyond provider-specific formatting.

### `tools`

`tools` owns callable capabilities.

Expected responsibilities:

- Define a `Tool` protocol.
- Expose Chat Completions compatible tool schemas.
- Register tools by stable name.
- Validate model requested tool names and arguments.
- Execute tools.
- Return normalized `ToolResult` objects.

The runner should depend on `ToolRegistry`, not concrete tool implementations.

### `skills`

`skills` owns optional behavior packs and prompt fragments.

Initial skills should be lightweight. A skill is not a separate agent. It is a structured source of instructions and optional metadata that can be included in the context builder.

Expected responsibilities:

- Define a `Skill` data model or protocol.
- Register available skills.
- Select active skills for a run.
- Expose skill prompt fragments to the context builder.

Future responsibilities may include skill discovery from the filesystem, skill-specific tools, and skill activation rules.

### `context`

`context` owns prompt and message assembly.

It composes:

- Base system prompt.
- Runtime policy prompt.
- Active skills prompt.
- Tool usage prompt, if needed.
- Conversation history.
- Current user input.
- Previous tool results inside the current run.

Expected responsibilities:

- Build provider-ready messages.
- Keep system prompt assembly in one place.
- Normalize message shapes.
- Reserve extension points for trimming, summarization, and token budgeting.

`context` should not request models or execute tools.

### `state.py`

`state.py` owns runtime state containers.

Likely types:

- `ConversationState`: multi-turn session history and metadata.
- `RunState`: state for one user turn and its ReAct iterations.
- `IterationState`: optional per-iteration diagnostic state.

State types should be plain and serializable where practical.

### `types.py`

`types.py` owns shared cross-module types that would otherwise create circular imports.

Likely types:

- `ChatMessage`
- `ChatRequest`
- `ChatResponse`
- `ModelToolCall`
- `Usage`
- `AgentRunSpec`
- `AgentRunResult`

If a type belongs clearly to one submodule, keep it there. Use `types.py` only for genuinely shared contracts.

## Core Data Flow

For one conversation turn:

```text
ConversationLoop
  -> receives user input
  -> loads ConversationState
  -> calls AgentRunner.run(...)

AgentRunner
  -> initializes RunState
  -> ContextBuilder builds messages
  -> ToolRegistry exposes schemas
  -> LLMProvider.chat_completion(...)
  -> receives ChatResponse
  -> if tool calls:
       ToolRegistry.execute(...)
       append tool results
       continue next iteration
     else:
       return AgentRunResult

ConversationLoop
  -> persists final assistant message
  -> returns response to caller
```

## Initial Public Contracts

The exact implementation can evolve, but the first version should keep these contracts clear.

### Provider

```python
class LLMProvider(Protocol):
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        ...
```

### Tool

```python
class Tool(Protocol):
    name: str
    description: str

    def schema(self) -> dict:
        ...

    def execute(self, arguments: dict) -> ToolResult:
        ...
```

### Skill

```python
class Skill(Protocol):
    name: str

    def prompt(self) -> str:
        ...
```

### Runner

```python
class AgentRunner:
    def run(self, user_input: str, conversation: ConversationState) -> AgentRunResult:
        ...
```

### Loop

```python
class ConversationLoop:
    def run(self) -> None:
        ...
```

The concrete loop interface may vary by frontend. For example, a CLI loop may block on `input()`, while an API loop may expose `handle_user_message(...)`.

## Error Handling

Initial error handling should be explicit and simple:

- Provider transport, authentication, timeout, and rate-limit errors become normalized provider exceptions.
- Successful provider responses, including model-side refusal or tool-call finish reasons, become `ChatResponse` values.
- Unknown tool names produce tool error results visible to the model.
- Invalid tool arguments produce tool error results visible to the model.
- Tool execution exceptions are caught by `ToolRegistry` and returned as failed `ToolResult`.
- `AgentRunner` stops with a structured failure if max iterations is reached.

The runner should not crash on ordinary model/tool mistakes. It should convert recoverable issues into messages the model can respond to.

## Extensibility Path

### Providers

Start with one provider interface and Chat Completions semantics. Add concrete providers later under `agent/providers/`.

Potential future files:

```text
agent/providers/openai.py
agent/providers/deepseek.py
agent/providers/anthropic_chat_compat.py
```

Each provider should convert to and from the same internal `ChatRequest` and `ChatResponse` contracts.

### Tools

Tools should be added without changing runner logic:

```text
agent/tools/web_search.py
agent/tools/file_read.py
agent/tools/shell.py
```

Tool policy can be introduced later as a separate layer if needed.

### Skills

Skills should initially contribute prompt fragments. Later they may contribute:

- Tool dependencies.
- Activation rules.
- Metadata.
- Filesystem-based skill loading.

### Context

Context can evolve from simple concatenation to managed context assembly:

- Message trimming.
- Conversation summarization.
- Tool result compaction.
- Token budget estimation.
- Prompt section ordering.

These changes should remain behind `ContextBuilder`.

## Testing Strategy

The first implementation should include focused tests for module boundaries:

- Runner stops when the provider returns a final answer.
- Runner executes a requested tool and sends the result back to the provider.
- Runner stops at `max_iterations`.
- Tool registry rejects unknown tools with a normalized tool error.
- Context builder assembles system, skills, tools, history, and current input in the expected order.
- Conversation loop calls runner once per user turn and persists final messages.

Provider tests should use fake providers first. Real provider integration tests can come later and should not be required for normal unit test runs.

## Implementation Order

1. Define shared types and state objects.
2. Define provider protocol and a fake provider for tests.
3. Define tool protocol and registry.
4. Define skill protocol and registry.
5. Define context builder.
6. Implement `AgentRunner` ReAct loop.
7. Implement minimal `ConversationLoop`.
8. Add focused tests around runner, tools, context, and loop.

This order keeps each module independently testable and avoids building the runner around incomplete implicit contracts.

## Out of Scope For First Version

- Streaming responses.
- Parallel tool execution.
- Long-term memory.
- Filesystem skill discovery.
- Rich tracing UI.
- Provider-specific advanced features.
- Top-level package extraction.
- Full token budgeting and summarization.

These are intentionally deferred so the first agent core stays understandable and easy to revise.
