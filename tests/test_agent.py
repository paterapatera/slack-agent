import pytest
from langchain_core.messages import AIMessage

import slack_agent.agent as agent_mod


class _FakeGraph:
    async def ainvoke(self, inputs: dict):
        # Simulate agent returning a list of messages with last being AI
        return {
            "messages": [
                AIMessage(content="first"),
                AIMessage(content="final answer"),
            ]
        }


@pytest.mark.asyncio
async def test_invoke_agent_returns_last_ai_message(monkeypatch):
    monkeypatch.setattr(agent_mod, "get_agent_graph", lambda: _FakeGraph())

    result = await agent_mod.invoke_agent("hello")

    assert result == "final answer"
