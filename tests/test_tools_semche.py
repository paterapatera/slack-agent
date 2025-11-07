from __future__ import annotations

from typing import Any

import pytest

from slack_agent.mcp import semche as semche_client
from slack_agent.tools.semche import semche_search


def test_semche_tool_delegates_to_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_search(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "status": "success",
            "message": "ok",
            "results": [],
            "count": 0,
            "query_vector_dimension": None,
            "persist_directory": "./chroma_db",
        }

    monkeypatch.setattr(semche_client, "search", _fake_search)

    resp = semche_search(
        query="hello",
        top_k=2,
        file_type="md",
        include_documents=False,
        max_content_length=200,
    )

    assert resp["status"] == "success"
    assert calls and calls[0]["query"] == "hello"
    assert calls[0]["top_k"] == 2
    assert calls[0]["file_type"] == "md"
    assert calls[0]["include_documents"] is False
    assert calls[0]["max_content_length"] == 200
