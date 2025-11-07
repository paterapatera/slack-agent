"""Semche ツール定義: search のみ。

LangChain の Tool で包むのは呼び出し側（agent.py）で行います。
ここでは純粋な関数として公開します。
"""

from __future__ import annotations

from ..mcp import semche as semche_client


def semche_search(
    query: str,
    top_k: int | None = 5,
    file_type: str | None = None,
    include_documents: bool | None = True,
    max_content_length: int | None = None,
) -> semche_client.SearchResponse:
    """Semche のハイブリッド検索を実行します。

    パラメータ:
    - query: 検索文字列（必須）
    - top_k: 取得件数（既定: 5）
    - file_type: メタデータ file_type でフィルタ
    - include_documents: 本文を含めるか（既定: True）
    - max_content_length: 本文の最大文字数（None で全文）

    戻り値は Semche README の返却スキーマに準拠した dict。
    """
    return semche_client.search(
        query=query,
        top_k=top_k,
        file_type=file_type,
        include_documents=include_documents,
        max_content_length=max_content_length,
    )


__all__ = ["semche_search"]
