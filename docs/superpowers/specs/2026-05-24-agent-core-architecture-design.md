# Agent Core Architecture Design

Date: 2026-05-24

## Goal

Build a simple, extensible agent core for `hello-agents`.

The first implementation should support Chat Completions style providers, an async ReAct-style tool reasoning loop, multi-turn conversation orchestration, prompt-only skills, tools, and prompt context assembly without placing all logic in one file.

## Design Principles

- Keep the initial package small and easy to change.
- Put agent core modules under the `agent` package first.
- Separate responsibilities by lifecycle: conversation, run, provider call, tool execution, and context assembly.
- Keep orchestration separate from policy decisions.
- Make providers, tools, and skills extensible through async protocols and registries.
- Avoid early extraction into top-level packages until public APIs stabilize.
- Keep provider implementations focused on model requests only.
- Keep the first `Skill` abstraction prompt-only; do not mix it with tool packs or activation engines.

## Package Layout

Initial layout:

```text
agent/
  __init__.py
  loop.py
  runner.py
  types.py
  conversation/
    __init__.py
    policy.py
    state.py
  runtime/
    __init__.py
    state.py
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
- Load the current `ConversationState`.
- Call `AgentRunner.run(...)` for one user turn.
- Persist the final assistant response and updated conversation state.
- Ask a separate `ConversationPolicy` whether the loop should continue.
- Provide an integration point for CLI, API, WebSocket, or UI frontends.

`loop` does not execute tools directly, does not implement the ReAct loop, and does not own policy rules such as exit commands, max turns, or session expiration.

Conceptually:

```text
while policy.should_continue(conversation):
  user_input = receive()
  result = await runner.run(user_input, conversation)
  conversation = persist(result)
  respond(result.final_message)
```

### `conversation/policy.py`

`ConversationPolicy` owns conversation continuation policy.

Expected responsibilities:

- Decide whether a conversation is still active.
- Handle simple policies such as explicit exit commands, max user turns, or timeout markers.
- Stay independent from provider calls and tool execution.
- Expose a small contract that the loop can call before or after a user turn.

This prevents `loop.py` from becoming both an orchestrator and a policy engine.

### `conversation/state.py`

`ConversationState` owns multi-turn session state.

This state has a longer lifecycle than a single agent run and may be persisted by a CLI, server, or test harness.

Likely fields:

- Conversation id.
- Ordered conversation messages.
- Active skill names.
- User/session metadata needed by tools.
- Turn count.
- Created/updated timestamps if persistence is added.

Conversation state should not contain per-iteration ReAct scratch data.

### `runtime/state.py`

Runtime state owns one `AgentRunner.run(...)` execution.

Likely types:

- `RunState`: messages and metadata for one user turn.
- `IterationState`: one model/tool iteration inside the ReAct loop.
- `ToolExecutionContext`: the narrow tool-visible execution context derived from the run and conversation.

This state is short-lived and should be discarded or compacted after the runner returns an `AgentRunResult`.

### `runner.py`

`runner` owns one agent run for a single user turn.

It handles the internal async ReAct-style model/tool reasoning loop:

- Build model-ready context for the current run.
- Await the provider request.
- Inspect the model response.
- Execute requested tool calls through `ToolRegistry`.
- Append tool results to the run messages.
- Continue until final answer, max iterations, cancellation, or unrecoverable failure.
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

This whole inner sequence is one `await AgentRunner.run(...)`.

### `providers`

`providers` owns model transport.

The provider layer should not know about the conversation loop, skills registry internals, or tool execution policy. It accepts a normalized chat request and returns a normalized chat response.

Initial target: Chat Completions style request/response.

Expected responsibilities:

- Convert internal `ChatRequest` into provider-specific API payloads.
- Await the provider API request.
- Convert provider-specific responses into internal `ChatResponse`.
- Normalize tool calls, finish reasons, usage, and errors.
- Expose a contract that can later support streaming without replacing the provider abstraction.

Non-responsibilities:

- No ReAct loop.
- No direct tool execution.
- No session persistence.
- No prompt policy decisions beyond provider-specific formatting.

### `tools`

`tools` owns callable capabilities.

Expected responsibilities:

- Define an async `Tool` protocol.
- Expose Chat Completions compatible tool schemas.
- Register tools by stable name.
- Validate model requested tool names and arguments.
- Execute tools with a `ToolExecutionContext`.
- Return normalized `ToolResult` objects.

The runner should depend on `ToolRegistry`, not concrete tool implementations.

### `skills`

`skills` owns prompt-only behavior fragments for the first version.

A `Skill` is not a separate agent, not a tool bundle, and not an activation engine. It is a structured source of instructions that can be included by the context builder when the caller or conversation state marks it active.

Expected responsibilities:

- Define a prompt-only `Skill` data model or protocol.
- Register available skills.
- Resolve active skill names into ordered prompt fragments.
- Expose skill prompt fragments to the context builder.

Out of scope for the first skill abstraction:

- Skill-specific tools.
- Skill-owned activation rules.
- Nested agents.
- Filesystem discovery.

If those become necessary, introduce a separate abstraction such as `SkillPackage` or `CapabilityPack` instead of expanding the initial `Skill` protocol until it has multiple unrelated meanings.

### `context`

`context` owns prompt and message assembly.

It composes:

- Base system prompt.
- Runtime policy prompt.
- Active skill prompts.
- Tool usage prompt, if needed.
- Conversation history.
- Current user input.
- Previous tool results inside the current run.

Expected responsibilities:

- Build provider-ready messages.
- Keep system prompt assembly in one place.
- Normalize message shapes.
- Reserve extension points for trimming, summarization, and token budgeting.

`context` should not request models, execute tools, or decide whether a conversation continues.

### `types.py`

`types.py` owns shared cross-module contracts that would otherwise create circular imports.

Likely types:

- `ChatMessage`
- `ChatRequest`
- `ChatResponse`
- `ChatResponseChunk`
- `ChatStreamEvent`
- `ModelToolCall`
- `Usage`
- `AgentRunSpec`
- `AgentRunResult`

If a type belongs clearly to one submodule, keep it there. Use `types.py` only for genuinely shared contracts.

If streaming and non-streaming contracts grow beyond a few shared dataclasses, split `types.py` into a `types/` package, for example `types/chat.py` and `types/streaming.py`, rather than letting one file become an unstructured dump of unrelated contracts.

## Core Data Flow

For one conversation turn:

```text
ConversationLoop
  -> receives user input
  -> loads ConversationState
  -> asks ConversationPolicy if input/session can continue
  -> calls await AgentRunner.run(...)

AgentRunner
  -> initializes RunState
  -> ContextBuilder builds messages
  -> ToolRegistry exposes schemas
  -> await LLMProvider.chat_completion(...)
  -> receives ChatResponse
  -> if tool calls:
       build ToolExecutionContext
       await ToolRegistry.execute(...)
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
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        ...
```

Streaming is not required in the first implementation, but the type layer should reserve streaming concepts now so the provider abstraction does not need to be replaced later:

```python
class StreamingLLMProvider(LLMProvider, Protocol):
    async def stream_chat_completion(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatStreamEvent]:
        ...
```

### Tool

```python
@dataclass
class ToolExecutionContext:
    run_id: str
    conversation_id: str | None
    user_id: str | None
    metadata: dict[str, Any]
```

```python
class Tool(Protocol):
    name: str
    description: str

    async def schema(self) -> dict[str, Any]:
        ...

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        ...
```

Tool context gives tools access to session metadata, permissions, user identity, and the current run id without forcing those concerns into the tool argument JSON generated by the model. It intentionally does not expose the full `RunState`; tools should not depend on runner internals.

### Skill

```python
class Skill(Protocol):
    name: str

    def prompt(self) -> str:
        ...
```

Skill activation is not owned by `Skill`. The first version should use explicit active skill names from the caller or `ConversationState`.

### Conversation Policy

```python
class ConversationPolicy(Protocol):
    async def should_continue(
        self,
        conversation: ConversationState,
    ) -> bool:
        ...

    async def accept_user_input(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> bool:
        ...
```

`should_continue(...)` handles session-level continuation checks. `accept_user_input(...)` handles input-level checks such as explicit exit commands. Both are async so policies can later consult external session stores without changing the loop contract.

### Runner

```python
class AgentRunner:
    async def run(
        self,
        user_input: str,
        conversation: ConversationState,
    ) -> AgentRunResult:
        ...
```

### Loop

```python
class ConversationLoop:
    async def run(self) -> None:
        ...
```

The concrete loop interface may vary by frontend. For example, a CLI loop may await console input through an adapter, while an API loop may expose `async handle_user_message(...)`.

## Streaming Compatibility

Full streaming behavior is deferred, but the initial contracts should not make streaming a breaking change.

First-version requirements:

- Keep `ChatResponse` as the assembled final model response.
- Define `ChatStreamEvent` and `ChatResponseChunk` early, even if no provider implements them yet.
- Keep provider request types shared between non-streaming and streaming calls.
- Keep runner output compatible with a future event stream, for example by making iterations explicit in `RunState`.

Out of scope for the first implementation:

- Streaming UI adapters.
- Partial tool-call execution while deltas are still arriving.
- Token-by-token runner event emission.
- Backpressure handling.

This makes streaming an additive provider capability instead of a redesign of the provider layer.

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

Start with one async provider interface and Chat Completions semantics. Add concrete providers later under `agent/providers/`.

Potential future files:

```text
agent/providers/openai.py
agent/providers/deepseek.py
agent/providers/anthropic_chat_compat.py
```

Each provider should convert to and from the same internal `ChatRequest` and `ChatResponse` contracts. Providers that support streaming can additionally implement `StreamingLLMProvider`.

### Tools

Tools should be added without changing runner logic:

```text
agent/tools/web_search.py
agent/tools/file_read.py
agent/tools/shell.py
```

Tool policy can be introduced later as a separate layer if needed. Tool implementations receive `ToolExecutionContext`, so they do not need to depend directly on conversation storage or runner internals.

### Skills

Skills should initially contribute prompt fragments only. Later, if the system needs bundled prompts, tools, resources, and activation rules, add a separate package-level abstraction rather than overloading `Skill`.

### Context

Context can evolve from simple concatenation to managed context assembly:

- Message trimming.
- Conversation summarization.
- Tool result compaction.
- Token budget estimation.
- Prompt section ordering.

These changes should remain behind `ContextBuilder`.

## Testing Strategy

The first implementation should include focused async tests for module boundaries:

- Runner stops when the provider returns a final answer.
- Runner awaits a requested tool and sends the result back to the provider.
- Runner passes `ToolExecutionContext` into tool execution.
- Runner does not expose full `RunState` to tools.
- Runner stops at `max_iterations`.
- Tool registry rejects unknown tools with a normalized tool error.
- Tool registry awaits tool schemas when building provider tool definitions.
- Context builder assembles system, skills, tools, history, and current input in the expected order.
- Conversation loop delegates continuation decisions to `ConversationPolicy`.
- Conversation loop calls runner once per user turn and persists final messages.

Provider tests should use fake async providers first. Real provider integration tests can come later and should not be required for normal unit test runs.

## Implementation Order

1. Define shared chat/provider types, including streaming-compatible response chunk/event types.
2. Define conversation state and conversation policy.
3. Define runtime state and `ToolExecutionContext`.
4. Define async provider protocol and a fake provider for tests.
5. Define async tool protocol and registry, including async schema loading.
6. Define prompt-only skill protocol and registry.
7. Define context builder.
8. Implement async `AgentRunner` ReAct loop.
9. Implement minimal async `ConversationLoop`.
10. Add focused async tests around runner, tools, context, policy, and loop.

This order keeps each module independently testable and avoids building the runner around incomplete implicit contracts.

## Out of Scope For First Version

- Streaming UI and event delivery.
- Parallel tool execution.
- Long-term memory.
- Filesystem skill discovery.
- Skill-owned tools or activation rules.
- Rich tracing UI.
- Provider-specific advanced features.
- Top-level package extraction.
- Full token budgeting and summarization.

These are intentionally deferred so the first agent core stays understandable and easy to revise without closing the door on async execution, tool context, or future streaming.
