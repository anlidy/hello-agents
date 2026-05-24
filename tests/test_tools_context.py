from dataclasses import dataclass

import pytest

from agent.context.builder import ContextBuilder
from agent.conversation.state import ConversationState
from agent.runtime.state import ToolExecutionContext
from agent.skills.base import StaticSkill
from agent.skills.registry import SkillRegistry
from agent.tools.base import ToolResult
from agent.tools.registry import ToolRegistry
from agent.types import ChatMessage


@dataclass
class EchoTool:
    name: str = "echo"
    description: str = "Echo text"

    async def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object"},
            },
        }

    async def execute(self, arguments, context):
        return ToolResult(name=self.name, content=f"{context.user_id}:{arguments['text']}")


@pytest.mark.asyncio
async def test_tool_registry_awaits_schema_and_passes_context():
    registry = ToolRegistry([EchoTool()])
    schemas = await registry.schemas()
    result = await registry.execute(
        "echo",
        {"text": "hi"},
        ToolExecutionContext(run_id="r1", conversation_id="c1", user_id="u1", metadata={}),
    )

    assert schemas[0]["function"]["name"] == "echo"
    assert result.content == "u1:hi"
    assert result.error is None


@pytest.mark.asyncio
async def test_unknown_tool_returns_normalized_error():
    registry = ToolRegistry([])
    result = await registry.execute(
        "missing",
        {},
        ToolExecutionContext(run_id="r1", conversation_id=None, user_id=None, metadata={}),
    )

    assert result.error == "unknown_tool"
    assert "missing" in result.content


@pytest.mark.asyncio
async def test_context_builder_orders_system_skills_history_and_user_input():
    skills = SkillRegistry([StaticSkill(name="coding", instructions="Prefer small modules.")])
    builder = ContextBuilder(base_system_prompt="You are an agent.", skill_registry=skills)
    conversation = ConversationState(
        id="c1",
        messages=[ChatMessage(role="assistant", content="previous")],
        active_skill_names=["coding"],
    )

    messages = await builder.build_messages("current", conversation, [])

    assert messages[0].role == "system"
    assert "You are an agent." in messages[0].content
    assert "Prefer small modules." in messages[0].content
    assert [m.content for m in messages[1:]] == ["previous", "current"]
