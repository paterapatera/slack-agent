"""Semche MCP クライアントの薄いラッパー（検索のみ）。

現時点では本番の MCP クライアント実装に依存せず、
環境変数 `SEMCHE_MOCK=1` のときにモックレスポンスを返します。
未設定時は実装準備中のため RuntimeError を送出します。

将来的には modelcontextprotocol などのクライアントを用いて、
STDIO/HTTP いずれかの経路で Semche サーバーへ接続してツールを呼び出します。
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent


class SearchResult(TypedDict, total=False):
    filepath: str
    score: float
    document: str
    metadata: dict[str, Any]


class SearchResponse(TypedDict):
    status: str
    message: str
    results: list[SearchResult]
    count: int
    query_vector_dimension: int | None
    persist_directory: str | None


@dataclass(frozen=True)
class SemcheClientSettings:
    path: str | None
    url: str | None
    timeout: int
    chroma_dir: str | None

    @staticmethod
    def from_env() -> SemcheClientSettings:
        path = os.getenv("MCP_SEMCHE_PATH")
        url = os.getenv("MCP_SEMCHE_URL")
        timeout_str = os.getenv("MCP_SEMCHE_TIMEOUT", "10")
        chroma_dir = os.getenv("SEMCHE_CHROMA_DIR")
        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 10
        return SemcheClientSettings(path=path, url=url, timeout=timeout, chroma_dir=chroma_dir)


def get_client() -> SemcheClientSettings:
    """現時点では設定を返すだけ（将来ここで接続/初期化を行う）。"""
    return SemcheClientSettings.from_env()


def search(
    query: str,
    top_k: int | None = 5,
    file_type: str | None = None,
    include_documents: bool | None = True,
    max_content_length: int | None = None,
) -> SearchResponse:
    """Semche の search ツール呼び出し（実接続 + モック対応）。

    パラメータは Semche README の仕様に準拠。
    実装統合までの間は SEMCHE_MOCK=1 の場合にモック結果を返す。
    それ以外は RuntimeError を送出して、実装未完了を通知する。
    """
    settings = get_client()

    if os.getenv("SEMCHE_MOCK") == "1":
        # 簡易モック応答
        item: SearchResult = {
            "filepath": "/docs/example.txt",
            "score": 0.75,
            "metadata": {"file_type": file_type or "none", "updated_at": "2025-11-07T00:00:00"},
        }
        if include_documents:
            item["document"] = "This is a mocked search result document."
        return {
            "status": "success",
            "message": "ハイブリッド検索が完了しました (mock)",
            "results": [item],
            "count": 1,
            "query_vector_dimension": None,
            "persist_directory": settings.chroma_dir or "./chroma_db",
        }

    # 実接続: stdio（MCP_SEMCHE_PATH）を使用
    arguments: dict[str, Any] = {
        "query": query,
    }
    if top_k is not None:
        arguments["top_k"] = int(top_k)
    if file_type is not None:
        arguments["file_type"] = file_type
    if include_documents is not None:
        arguments["include_documents"] = bool(include_documents)
    if max_content_length is not None:
        arguments["max_content_length"] = int(max_content_length)

    def _select_search_tool_name(tool_names: list[str]) -> str:
        # 優先: "search" 完全一致 → ".search" 終端 → 部分一致
        lowered = [t.lower() for t in tool_names]
        if "search" in lowered:
            return tool_names[lowered.index("search")]
        for i, t in enumerate(lowered):
            if t.endswith(".search"):
                return tool_names[i]
        for i, t in enumerate(lowered):
            if "search" in t:
                return tool_names[i]
        # 見つからなければ最初のツール名（異常系）
        return tool_names[0] if tool_names else "search"

    async def _call_over_stdio() -> SearchResponse:
        # stdio 経由でサーバープロセスを起動
        path = settings.path or ""
        env = {k: v for k, v in os.environ.items()}
        if settings.chroma_dir:
            env["SEMCHE_CHROMA_DIR"] = settings.chroma_dir

        # パスの扱い: ディレクトリの場合は既定の server スクリプトを推定
        server_py = os.path.join(path, "src/semche/mcp_server.py") if os.path.isdir(path) else path

        if not os.path.isabs(server_py):
            server_py = os.path.abspath(server_py)

        params = StdioServerParameters(
            command="uv",
            args=["run", "python", server_py],
            env=env,
        )

        timeout = max(1, settings.timeout)
        async with stdio_client(params) as (read, write):  # noqa: SIM117
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                tools_resp = await asyncio.wait_for(session.list_tools(), timeout=timeout)
                tool_names = [t.name for t in tools_resp.tools]
                tool_name = _select_search_tool_name(tool_names)
                result: CallToolResult = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments=arguments), timeout=timeout
                )
                return _parse_call_tool_result(result, settings)

    def _run(
        coro: Coroutine[Any, Any, SearchResponse],
    ) -> SearchResponse:
        # 実行中ループがある場合は別スレッドでコルーチンを走らせる
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result_box: dict[str, SearchResponse] = {}
        err_box: dict[str, BaseException] = {}

        def runner() -> None:
            try:
                result_box["v"] = asyncio.run(coro)
            except BaseException as e:  # noqa: BLE001
                err_box["e"] = e

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join()
        if "e" in err_box:
            raise err_box["e"]
        return result_box["v"]

    def _parse_call_tool_result(
        result: CallToolResult, cfg: SemcheClientSettings
    ) -> SearchResponse:
        # 1) structuredContent が Semche スキーマの dict で来る場合
        if getattr(result, "structuredContent", None):
            sc = cast(dict[str, Any], result.structuredContent)
            return _normalize_semche_response(sc, cfg)

        # 2) content の TextContent に JSON 文字列が入っている場合
        for block in result.content:
            if isinstance(block, TextContent):
                text = block.text
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        return _normalize_semche_response(cast(dict[str, Any], data), cfg)
                except Exception:
                    # JSON でない → fallthrough
                    pass

        # 3) それ以外は簡易的に success としてテキストを message に格納
        joined = "\n".join([b.text for b in result.content if isinstance(b, TextContent)])
        return {
            "status": "success",
            "message": joined or "search executed",
            "results": [],
            "count": 0,
            "query_vector_dimension": None,
            "persist_directory": cfg.chroma_dir or "./chroma_db",
        }

    def _normalize_semche_response(
        data: dict[str, Any], cfg: SemcheClientSettings
    ) -> SearchResponse:
        # 必須キーの補完と型の整形
        status = str(data.get("status", "success"))
        message = str(data.get("message", ""))
        results_data = data.get("results") or []
        results: list[SearchResult] = []
        for r in results_data:
            if not isinstance(r, dict):
                continue
            item: SearchResult = {
                "filepath": str(r.get("filepath", "")),
                "score": float(r.get("score", 0.0)),
                "metadata": cast(dict[str, Any], r.get("metadata") or {}),
            }
            if "document" in r and r.get("document") is not None:
                item["document"] = str(r.get("document"))
            results.append(item)

        count = int(data.get("count", len(results)))
        qdim = data.get("query_vector_dimension")
        qdim_val = int(qdim) if isinstance(qdim, int) else None
        persist_dir = data.get("persist_directory") or cfg.chroma_dir or "./chroma_db"

        return {
            "status": status,
            "message": message,
            "results": results,
            "count": count,
            "query_vector_dimension": qdim_val,
            "persist_directory": cast(str | None, persist_dir),
        }

    # 実運用: stdio のみ
    if settings.path:
        return _run(_call_over_stdio())

    raise RuntimeError(
        "Semche MCP 接続先が未設定です。MCP_SEMCHE_PATH を設定してください。"
    )
