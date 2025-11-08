from __future__ import annotations

import asyncio
import atexit
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
from .text import clean_mention_text

logger = logging.getLogger(__name__)

# --- MCP tools auto-load (once) ---
_tools_lock = asyncio.Lock()
_cached_tools: list[Any] | None = None


class MCPConnectionManager:
    """永続 MCP セッションをプロセス内で 1 回だけ開始・保持するシングルトン。

    - stdio_client と ClientSession を手動で __aenter__ し、__aexit__ はプロセス終了時に実行。
    - LangChain 用の工具（tools）は初回に取得してキャッシュ。
    - 既存のモジュールレベルキャッシュ（_cached_tools）との互換を維持するため、
      load_mcp_tools_once() 側で _cached_tools をセットする。
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._started: bool = False
        self._stdio_cm: Any | None = None
        self._session_cm: Any | None = None
        self._session: ClientSession | None = None
        self._tools: list[Any] | None = None

    async def ensure_started(self) -> None:
        if self._started:
            return
        async with self._lock:
            if self._started:
                return

            try:
                # 遅延 import（依存未導入時のメッセージをわかりやすくする）
                from langchain_mcp_adapters.tools import load_mcp_tools  # noqa: F401
            except Exception as e:  # noqa: BLE001
                logger.error("langchain_mcp_adapters が見つかりません: %s", e)
                raise RuntimeError(
                    "langchain_mcp_adapters が未導入のため MCP ツールの自動ロードに失敗しました"
                ) from e

            # 接続先（Semche MCP サーバ）: 環境変数を利用
            path = os.getenv("MCP_SEMCHE_PATH", "")
            if not path:
                raise RuntimeError("MCP_SEMCHE_PATH が未設定のため MCP 接続を開始できません")

            timeout = int(os.getenv("MCP_SEMCHE_TIMEOUT", 10))
            safe_timeout = max(1, timeout)

            chroma_dir = os.getenv("SEMCHE_CHROMA_DIR")
            env = dict(os.environ)
            if chroma_dir:
                env["SEMCHE_CHROMA_DIR"] = chroma_dir

            if not os.path.isdir(path):
                raise RuntimeError(f"MCP_SEMCHE_PATH はディレクトリを指定してください: {path}")

            work_dir = os.path.abspath(path)
            server_rel = "src/semche/mcp_server.py"
            server_full = os.path.join(work_dir, server_rel)
            if not os.path.exists(server_full):
                raise RuntimeError(f"MCP サーバースクリプトが見つかりません: {server_full}")

            params = StdioServerParameters(
                command="uv",
                args=["run", "--directory", work_dir, "python", server_rel],
                env=env,
            )

            # context manager を手動でオープンし保持（クローズは close() で）
            try:
                self._stdio_cm = stdio_client(params)
                read, write = await self._stdio_cm.__aenter__()
                self._session_cm = ClientSession(read, write)
                self._session = await self._session_cm.__aenter__()

                await asyncio.wait_for(self._session.initialize(), timeout=safe_timeout)

                # ツール取得（実体は load_mcp_tools を load_mcp_tools_once で呼ぶ）
                # ここではセッション有効化までを担当。ツールの取得は呼び出し元で行う。
                self._started = True
            except Exception:
                # 途中まで開いた場合はクリーンアップを試みる
                await self._safe_close()
                self._started = False
                raise

    async def _safe_close(self) -> None:
        try:
            if self._session_cm is not None:
                await self._session_cm.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._session_cm = None
            self._session = None

        try:
            if self._stdio_cm is not None:
                await self._stdio_cm.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._stdio_cm = None

    async def close(self) -> None:
        await self._safe_close()
        self._tools = None
        self._started = False
        # モジュールキャッシュもクリアして再初期化を許可
        global _cached_tools
        _cached_tools = None

    @property
    def session(self) -> ClientSession | None:
        return self._session

    def set_tools(self, tools: list[Any]) -> None:
        self._tools = tools

    def get_tools(self) -> list[Any]:
        if self._tools is None:
            raise RuntimeError("MCP ツールが初期化されていません")
        return self._tools


_mcp_manager = MCPConnectionManager()


def _register_atexit_close() -> None:
    def _close_sync() -> None:
        try:
            # 可能なら新しいイベントループでクローズを実行
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_mcp_manager.close())
            finally:
                loop.close()
        except Exception:
            # ベストエフォート。終了時例外は握りつぶす。
            pass

    atexit.register(_close_sync)


_register_atexit_close()


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

        # 永続セッションが未開始であれば開始
        await _mcp_manager.ensure_started()

        try:
            from langchain_mcp_adapters.tools import load_mcp_tools
        except Exception as e:  # noqa: BLE001
            logger.error("langchain_mcp_adapters が見つかりません: %s", e)
            raise RuntimeError(
                "langchain_mcp_adapters が未導入のため MCP ツールの自動ロードに失敗しました"
            ) from e

        session = _mcp_manager.session
        if session is None:
            raise RuntimeError("MCP セッションが初期化されていません")

        timeout = int(os.getenv("MCP_SEMCHE_TIMEOUT", 10))
        safe_timeout = max(1, timeout)

        try:
            tools = await asyncio.wait_for(load_mcp_tools(session), timeout=safe_timeout)
        except Exception as e:  # noqa: BLE001
            logger.error("MCP ツールの自動ロード中に失敗しました: %s", e, exc_info=True)
            raise RuntimeError("MCP ツールの自動ロードに失敗しました") from e

        if not tools:
            raise RuntimeError("MCP から取得できるツールが 0 件でした")

        tool_list = list(tools)
        _mcp_manager.set_tools(tool_list)
        _cached_tools = tool_list
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
            "必要に応じて MCP ツール（Semche の検索など）を利用してください。"
            "社内情報(仕様/コード/ドキュメント)や社内業務情報に関する質問では検索ツールの利用を検討。"
            "公開一般や基礎的質問ではツールを使わず直接回答。"
            "検索ツール利用時は include_documents=True, max_content_length=None (全文取得) を推奨。"
            "`file_type`は`実装内容`、`コード`、`JIRA`が指定できます。実装内容はコードを要約した日本語ドキュメントです。"
            "`実装内容`のファイル名はコードのファイル名の後ろに.exp.mdをつけたものです。"
            "取得本文は要約・引用で必要部分のみ提示。"
        )

        tools = await load_mcp_tools_once()

        graph: Any = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
        logger.info("Agent graph created with model=%s (tools=%d)", settings.model, len(tools))
        _agent_graph = graph
        return _agent_graph


async def invoke_agent(question: str, history: list[dict[str, Any]] | None = None) -> str:
    """Agents API 経由で質問を投げ、最終出力文字列を返します。

    Parameters
    - question: 現在のユーザーからの質問（メンション本文クリーニング済み）
    - history: Slack conversations.replies で取得したメッセージ辞書の配列（任意）
    """
    graph = await get_agent_graph()
    try:
        # Slack履歴をLangChainのmessagesへ粗くマッピング
        lc_messages: list[dict[str, str]] = []
        if history:
            for msg in history:
                raw = str(msg.get("text", "")).strip()
                text = clean_mention_text(raw) if raw else ""
                if not text:
                    continue
                # bot_idがあればassistant扱い、なければuser扱い（簡易規則）
                role = "assistant" if msg.get("bot_id") else "user"
                lc_messages.append({"role": role, "content": text})

        # 最後に今回の質問を追加（ユーザーメッセージ）
        lc_messages.append({"role": "user", "content": question})

        state = await graph.ainvoke({
            "messages": lc_messages,
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
