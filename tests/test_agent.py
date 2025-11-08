from __future__ import annotations

from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from langchain_core.messages import AIMessage

import slack_agent.agent as agent_mod


class _FakeGraph:
    async def ainvoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # Simulate agent returning a list of messages with last being AI
        return {
            "messages": [
                AIMessage(content="first"),
                AIMessage(content="final answer"),
            ]
        }


@pytest.mark.asyncio
async def test_invoke_agent_returns_last_ai_message(monkeypatch: MonkeyPatch) -> None:
    async def _fake_get_agent_graph() -> _FakeGraph:  # type: ignore[override]
        return _FakeGraph()

    monkeypatch.setattr(agent_mod, "get_agent_graph", _fake_get_agent_graph)

    result = await agent_mod.invoke_agent("hello")

    assert result == "final answer"


@pytest.mark.asyncio
async def test_invoke_agent_with_history(monkeypatch: MonkeyPatch) -> None:
    captured_inputs: dict[str, Any] = {}

    class _GraphHistory:
        async def ainvoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
            nonlocal captured_inputs
            captured_inputs = inputs
            return {
                "messages": [
                    AIMessage(content="contextual answer"),
                ]
            }

    async def _fake_get_agent_graph() -> _GraphHistory:  # type: ignore[override]
        return _GraphHistory()

    monkeypatch.setattr(agent_mod, "get_agent_graph", _fake_get_agent_graph)

    history = [
        {"text": "User: こんにちは"},
        {"text": "Bot: どうしましたか?", "bot_id": "BXXX"},
        {"text": "User: 質問があります"},
    ]

    result = await agent_mod.invoke_agent("最終の質問", history=history)

    assert result == "contextual answer"
    # messages順序: history(3件) + 現在の質問
    assert len(captured_inputs.get("messages", [])) == 4
    roles = [m["role"] for m in captured_inputs["messages"]]
    assert roles == ["user", "assistant", "user", "user"]
    assert captured_inputs["messages"][-1]["content"] == "最終の質問"
