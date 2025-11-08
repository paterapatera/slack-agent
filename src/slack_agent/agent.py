from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import SecretStr

from .config import OpenAISettings

logger = logging.getLogger(__name__)

# --- MCP tools auto-load (once) ---
_tools_lock = asyncio.Lock()
_cached_tools: list[Any] | None = None


async def load_mcp_tools_once() -> list[Any]:
    """MCP セッションから LangChain Tool 群を一度だけ自動ロードして返す。

    要件:
      - langchain_mcp_adapters が必須。未導入/失敗時は RuntimeError。
      - ツール0件や初期化失敗時も RuntimeError。
    キャッシュ:
      - プロセス中 1 回のみ接続・取得し、後続はキャッシュを返す。
    """
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools

    async with _tools_lock:
        if _cached_tools is not None:
            return _cached_tools

        try:
            # import は遅延評価にし、未導入時でもモジュール import エラーを回避
            from langchain_mcp_adapters.tools import load_mcp_tools
        except Exception as e:  # noqa: BLE001
            logger.error("langchain_mcp_adapters が見つかりません: %s", e)
            raise RuntimeError(
                "langchain_mcp_adapters が未導入のため MCP ツールの自動ロードに失敗しました"
            ) from e

        # 接続先（Semche MCP サーバ）: 環境変数を利用（既存実装と同等）
        path = os.getenv("MCP_SEMCHE_PATH", "")
        if not path:
            raise RuntimeError("MCP_SEMCHE_PATH が未設定のため MCP 接続を開始できません")

        timeout = int(os.getenv("MCP_SEMCHE_TIMEOUT", 10))
        safe_timeout = max(1, timeout)

        chroma_dir = os.getenv("SEMCHE_CHROMA_DIR")
        env = dict(os.environ)
        if chroma_dir:
            env["SEMCHE_CHROMA_DIR"] = chroma_dir

        # MCP_SEMCHE_PATH は Semche リポジトリのルートディレクトリを想定
        if not os.path.isdir(path):
            raise RuntimeError(f"MCP_SEMCHE_PATH はディレクトリを指定してください: {path}")

        # uv の実行ディレクトリを Semche 側プロジェクトルートに合わせる
        work_dir = os.path.abspath(path)
        server_rel = "src/semche/mcp_server.py"
        server_full = os.path.join(work_dir, server_rel)
        if not os.path.exists(server_full):
            raise RuntimeError(f"MCP サーバースクリプトが見つかりません: {server_full}")

        # --directory で作業ディレクトリを切り替えるため、起動は相対パスで十分
        params = StdioServerParameters(
            command="uv",
            args=["run", "--directory", work_dir, "python", server_rel],
            env=env,
        )

        try:
            async with stdio_client(params) as (read, write):  # noqa: SIM117
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=safe_timeout)
                    # 実体の Tool 群をアダプタで LangChain Tool へ変換
                    tools = await asyncio.wait_for(load_mcp_tools(session), timeout=safe_timeout)
        except Exception as e:  # noqa: BLE001
            logger.error("MCP ツールの自動ロード中に失敗しました: %s", e, exc_info=True)
            raise RuntimeError("MCP ツールの自動ロードに失敗しました") from e

        if not tools:
            raise RuntimeError("MCP から取得できるツールが 0 件でした")

        _cached_tools = list(tools)
        logger.info("MCP ツールを %d 件ロードしました", len(_cached_tools))
        return _cached_tools


# --- Agent graph (async, once) ---
_agent_lock = asyncio.Lock()
_agent_graph: Any | None = None


async def get_agent_graph() -> Any:
    """LangChain Agents API で compiled agent graph を生成（非同期・一度だけ）。

    - MCP ツールは load_mcp_tools_once() で自動ロード（失敗時はエラー）。
    - OpenAI 設定とシステムプロンプトは現状踏襲。
    """
    global _agent_graph
    if _agent_graph is not None:
        return _agent_graph

    async with _agent_lock:
        if _agent_graph is not None:
            return _agent_graph

        settings = OpenAISettings.from_env()
        llm = ChatOpenAI(
            model=settings.model, api_key=SecretStr(settings.api_key), temperature=0.7
        )

        system_prompt = (
            "Slackの返信には簡潔に答えてください。"
            "必要に応じて MCP ツールを利用して補助作業を行ってください。"
        )

        tools = await load_mcp_tools_once()

        graph: Any = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
        logger.info("Agent graph created with model=%s (tools=%d)", settings.model, len(tools))
        _agent_graph = graph
        return _agent_graph


async def invoke_agent(question: str) -> str:
    """Agents API 経由で質問を投げ、最終出力文字列を返します。"""
    graph = await get_agent_graph()
    try:
        state = await graph.ainvoke({
            "messages": [{"role": "user", "content": question}],
        })
        messages = state.get("messages", [])
        answer_text = None
        if messages:
            last = messages[-1]
            if isinstance(last, AIMessage):
                answer_text = last.content
            else:
                answer_text = getattr(last, "content", None) or getattr(last, "text", None)
        return str(answer_text) if answer_text is not None else ""
    except Exception as e:  # noqa: BLE001
        logger.error("Agent invocation failed: %s", e, exc_info=True)
        raise
