from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import slack_agent.agent as agent_mod


@pytest.mark.asyncio
async def test_persistent_session_single_open() -> None:
    """初回のみセッションが開かれ、2回目以降は再接続しない。"""
    # Arrange
    mock_tool = MagicMock()
    mock_tool.name = "dummy_tool"

    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return [mock_tool]

    # stdio_client / ClientSession の async context manager を手動オープンに合わせてモック
    stdio_enter_count = 0
    session_enter_count = 0

    mock_stdio_cm = AsyncMock()
    async def stdio_aenter():
        nonlocal stdio_enter_count
        stdio_enter_count += 1
        return MagicMock(), MagicMock()  # (read, write)
    mock_stdio_cm.__aenter__.side_effect = stdio_aenter
    mock_stdio_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session_cm = AsyncMock()
    mock_session = AsyncMock()
    async def session_aenter():
        nonlocal session_enter_count
        session_enter_count += 1
        return mock_session
    mock_session_cm.__aenter__.side_effect = session_aenter
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.initialize = AsyncMock()

    with (
        patch.dict("os.environ", {"MCP_SEMCHE_PATH": "/fake/path"}),
        patch("slack_agent.agent.os.path.isdir", return_value=True),
        patch("slack_agent.agent.os.path.exists", return_value=True),
        patch("slack_agent.agent.stdio_client", return_value=mock_stdio_cm),
        patch("slack_agent.agent.ClientSession", return_value=mock_session_cm),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        import sys
        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        # Reset module caches/state
        agent_mod._cached_tools = None
        await agent_mod._mcp_manager.close()

        # Act 1
        tools1 = await agent_mod.load_mcp_tools_once()
        # Act 2 (should reuse the same session)
        tools2 = await agent_mod.load_mcp_tools_once()

        # Assert
        assert tools1 is tools2
        assert len(tools1) == 1
        assert stdio_enter_count == 1
        assert session_enter_count == 1
        assert agent_mod._mcp_manager.session is not None


@pytest.mark.asyncio
async def test_close_clears_cache_and_allows_restart() -> None:
    """close() 後はキャッシュがクリアされ、再度ロードで再初期化される。"""
    mock_tool = MagicMock()
    mock_tool.name = "dummy_tool"

    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return [mock_tool]

    # カウンタ
    stdio_enter_count = 0

    mock_stdio_cm = AsyncMock()
    async def stdio_aenter():
        nonlocal stdio_enter_count
        stdio_enter_count += 1
        return MagicMock(), MagicMock()
    mock_stdio_cm.__aenter__.side_effect = stdio_aenter
    mock_stdio_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session_cm = AsyncMock()
    mock_session = AsyncMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.initialize = AsyncMock()

    with (
        patch.dict("os.environ", {"MCP_SEMCHE_PATH": "/fake/path"}),
        patch("slack_agent.agent.os.path.isdir", return_value=True),
        patch("slack_agent.agent.os.path.exists", return_value=True),
        patch("slack_agent.agent.stdio_client", return_value=mock_stdio_cm),
        patch("slack_agent.agent.ClientSession", return_value=mock_session_cm),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        import sys
        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        agent_mod._cached_tools = None
        await agent_mod._mcp_manager.close()

        # 初回ロード
        tools1 = await agent_mod.load_mcp_tools_once()
        assert len(tools1) == 1
        assert stdio_enter_count == 1

        # クローズ
        await agent_mod._mcp_manager.close()
        # 再ロード（再初期化されるはず）
        tools2 = await agent_mod.load_mcp_tools_once()
        assert len(tools2) == 1
        assert stdio_enter_count == 2  # 2回目の __aenter__ が呼ばれる


@pytest.mark.asyncio
async def test_partial_failure_cleanup() -> None:
    """初期化途中で失敗してもリソースがクリーンアップされる。"""
    mock_tool = MagicMock()
    mock_tool.name = "dummy_tool"

    async def fake_load_mcp_tools(session: Any) -> list[Any]:
        return [mock_tool]

    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_stdio_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session_cm = AsyncMock()
    mock_session = AsyncMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    # initialize で失敗させる
    async def fail_initialize():
        raise RuntimeError("init failed")
    mock_session.initialize = fail_initialize

    with (
        patch.dict("os.environ", {"MCP_SEMCHE_PATH": "/fake/path"}),
        patch("slack_agent.agent.os.path.isdir", return_value=True),
        patch("slack_agent.agent.os.path.exists", return_value=True),
        patch("slack_agent.agent.stdio_client", return_value=mock_stdio_cm),
        patch("slack_agent.agent.ClientSession", return_value=mock_session_cm),
        patch.dict(
            "sys.modules",
            {"langchain_mcp_adapters": MagicMock(), "langchain_mcp_adapters.tools": MagicMock()},
        ),
    ):
        import sys
        sys.modules["langchain_mcp_adapters.tools"].load_mcp_tools = fake_load_mcp_tools

        agent_mod._cached_tools = None
        await agent_mod._mcp_manager.close()

        with pytest.raises(RuntimeError, match="MCP ツールの自動ロードに失敗|init failed|初期化"):
            # ensure_started を直接呼ぶと load_mcp_tools まで進まないため、
            # load_mcp_tools_once() の中で initialize が呼ばれて落ちる経路を通す
            await agent_mod.load_mcp_tools_once()

        # 失敗後にセッションはクリアされていること
        assert agent_mod._mcp_manager.session is None
        # 再試行できるようにキャッシュは空
        assert agent_mod._cached_tools is None
