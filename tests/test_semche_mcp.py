from __future__ import annotations

import pytest

from slack_agent.mcp import semche as semche_client


@pytest.mark.parametrize(
    "include_docs,expected_has_doc",
    [(True, True), (False, False)],
)
def test_semche_search_mock_success(
    monkeypatch: pytest.MonkeyPatch,
    include_docs: bool,
    expected_has_doc: bool,
) -> None:
    # Setup mock mode and clear optional envs to exercise defaults
    monkeypatch.setenv("SEMCHE_MOCK", "1")
    monkeypatch.delenv("SEMCHE_CHROMA_DIR", raising=False)

    resp = semche_client.search(
        query="test query",
        top_k=3,
        file_type="animal",
        include_documents=include_docs,
        max_content_length=None,
    )

    assert resp["status"] == "success"
    assert resp["count"] == 1
    assert isinstance(resp["results"], list) and len(resp["results"]) == 1

    item = resp["results"][0]
    assert item["metadata"].get("file_type") in {"animal", "none"}

    if expected_has_doc:
        assert "document" in item and isinstance(item["document"], str)
    else:
        assert "document" not in item

    # default persist dir when SEMCHE_CHROMA_DIR is not set
    assert resp["persist_directory"] == "./chroma_db"


def test_semche_search_requires_path_without_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure not in mock mode and no PATH configured
    monkeypatch.delenv("SEMCHE_MOCK", raising=False)
    monkeypatch.delenv("MCP_SEMCHE_PATH", raising=False)

    with pytest.raises(RuntimeError) as ei:
        semche_client.search(query="q")

    assert "MCP_SEMCHE_PATH" in str(ei.value)
