"""MCP ツール自動ロード機能のテスト。

自動ロード成功/失敗/メモ化の3観点を検証。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import slack_agent.agent as agent_mod


@pytest.mark.asyncio
async def test_load_mcp_tools_once_success() -> None:
    """自動ロード成功: langchain_mcp_adapters が使用でき、ツールが返される。"""
    # モックツール
    mock_tool1 = MagicMock()
    mock_tool1.name = "semche_search"
    mock_tool2 = MagicMock()
    mock_tool2.name = "semche_list"

    # langchain_mcp_adapters.tools.load_mcp_tools をモック
    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return [mock_tool1, mock_tool2]

    # モックセッション（stdio_client / ClientSession）
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock()

    # stdio_client を差し替えて MCP 接続をスキップ
    with (
        patch.dict("os.environ", {"MCP_SEMCHE_PATH": "/fake/path"}),
        patch("slack_agent.agent.stdio_client") as mock_stdio,
        patch("slack_agent.agent.ClientSession", return_value=mock_session),
        patch("slack_agent.agent.os.path.isdir", return_value=True),
        patch("slack_agent.agent.os.path.exists", return_value=True),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        # stdio_client は async context manager として (read, write) を返す
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)

        # langchain_mcp_adapters.tools.load_mcp_tools を差し替え
        import sys

        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        # キャッシュクリア（他テストの影響回避）
        agent_mod._cached_tools = None

        # act
        tools = await agent_mod.load_mcp_tools_once()

        # assert
        assert len(tools) == 2
        assert tools[0].name == "semche_search"
        assert tools[1].name == "semche_list"


@pytest.mark.asyncio
async def test_load_mcp_tools_once_failure_no_path() -> None:
    """MCP_SEMCHE_PATH 未設定で RuntimeError が送出される。"""
    # arrange: 環境変数を空にする & アダプタはモックで用意（import エラーを回避）
    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return []

    with (
        patch.dict("os.environ", {}, clear=True),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        import sys

        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        # キャッシュクリア
        agent_mod._cached_tools = None

        # act & assert
        with pytest.raises(RuntimeError, match="MCP_SEMCHE_PATH が未設定"):
            await agent_mod.load_mcp_tools_once()


@pytest.mark.asyncio
async def test_load_mcp_tools_once_memoization() -> None:
    """2回目以降はセッション初期化を行わず、キャッシュを返す。"""
    # モックツール
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"

    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return [mock_tool]

    initialize_call_count = 0

    async def track_initialize() -> None:
        nonlocal initialize_call_count
        initialize_call_count += 1

    # mock_session を async context manager として機能させる
    mock_session = AsyncMock()
    mock_session.initialize = track_initialize
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.dict("os.environ", {"MCP_SEMCHE_PATH": "/fake/path"}),
        patch("slack_agent.agent.stdio_client") as mock_stdio,
        patch("slack_agent.agent.ClientSession", return_value=mock_session),
        patch("slack_agent.agent.os.path.isdir", return_value=True),
        patch("slack_agent.agent.os.path.exists", return_value=True),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        # stdio_client の async context manager モック
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_stdio_ctx = AsyncMock()
        mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_stdio_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_stdio.return_value = mock_stdio_ctx

        import sys

        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        # キャッシュクリア
        agent_mod._cached_tools = None

        # act: 1回目
        tools1 = await agent_mod.load_mcp_tools_once()
        # act: 2回目
        tools2 = await agent_mod.load_mcp_tools_once()

        # assert: 両方とも同じツールが返され、initialize は1回だけ呼ばれる
        assert len(tools1) == 1
        assert len(tools2) == 1
        assert tools1 is tools2  # 同一オブジェクト（キャッシュされている）
        assert initialize_call_count == 1
