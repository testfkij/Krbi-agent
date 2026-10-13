import asyncio
import json
from pathlib import Path

import pytest

from krbi_agent.core import ChatMessage, StreamEvent
from krbi_agent.custom_tools import _make_spec, load_definitions, save_definition, validate_definition
from krbi_agent.roles import ROLE_LABELS, assign_role, load_skill
from krbi_agent.storage import Store


def test_role_assignment_and_skills_library():
    assert assign_role("please fix this Python crash") == "fixer"
    assert assign_role("design responsive mobile layout") == "designer"
    assert assign_role("anything", "backend developer") == "backend-developer"
    assert len(ROLE_LABELS) >= 10
    assert "review" in load_skill("reviewer").lower()


def test_custom_tool_definitions_validate_and_persist(tmp_path):
    target = tmp_path / "tools.json"
    definition = {"name": "count_words", "description": "Count words", "kind": "word_count"}
    save_definition(definition, target)
    assert load_definitions(target) == [definition]
    with pytest.raises(ValueError):
        save_definition(definition, target)
    with pytest.raises(ValueError):
        validate_definition({"name": "shell", "description": "override", "kind": "word_count"})
    with pytest.raises(ValueError):
        validate_definition({"name": "danger", "description": "run code", "kind": "python"})


def test_custom_tool_executes_declared_behavior_only():
    async def run():
        spec = _make_spec({"name": "count_words", "description": "Count words", "kind": "word_count"})
        result = await spec.func({"value": "hello from KRBI"})
        assert result == {"words": 3, "characters": 15}
    asyncio.run(run())


def test_sqlite_messages_survive_store_restart_and_delete_cascades(tmp_path):
    root = tmp_path / "chats"
    store = Store(root)
    chat_id = store.new_chat("Example", "test-provider", "test-model")
    store.add_message(chat_id, ChatMessage("user", "persist this"))
    store.add_message(chat_id, ChatMessage("assistant", "saved"))
    store2 = Store(root)
    assert [item.content for item in store2.messages(chat_id)] == ["persist this", "saved"]
    assert store2.chats()[0].title == "Example"
    store2.delete(chat_id)
    assert store2.messages(chat_id) == []
    assert not list(root.glob(f"chat-{chat_id:06d}*.md"))


class _CapturingProvider:
    def __init__(self):
        self.messages = None
    async def stream_chat(self, messages, model, **kwargs):
        self.messages = messages
        yield StreamEvent("delta", delta="Task response verified")


class _Registry:
    def __init__(self, provider):
        self.provider = provider
    def get(self, name, api_key=None):
        return self.provider


def test_focus_task_is_supplied_to_agent_as_completion_objective(tmp_path):
    from krbi_agent.agent import Agent
    from krbi_agent.settings import Settings
    async def run():
        provider = _CapturingProvider()
        store = Store(tmp_path / "chats")
        chat_id = store.new_chat("Focused", "fake", "fake-model")
        agent = Agent(_Registry(provider), store, settings=Settings())
        events = [event async for event in agent.run(
            chat_id, "fake", "fake-model", "start work",
            focus_task="Finish the user task and verify the results",
        )]
        assert any(event.type == "done" for event in events)
        system_text = provider.messages[0].content
        assert "FOCUS MODE IS ACTIVE" in system_text
        assert "Finish the user task and verify the results" in system_text
        assert store.messages(chat_id)[-1].content == "Task response verified"
    asyncio.run(run())
