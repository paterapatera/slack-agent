# tools/semche.py の説明

LangChain ツールとして Semche 検索を公開する薄いラッパー関数を提供します。実体は `mcp/semche.py` の `search` を呼び出します。

## 主な関数

- `semche_search(query: str, top_k: int = 5, file_type: str | None = None, include_documents: bool | None = True, max_content_length: int | None = None) -> dict`
  - 引数をそのまま `mcp.semche.search` に委譲してレスポンス（dict）を返します。
  - 返却スキーマは Semche 側の仕様に準拠（`status`, `message`, `results`, `count`, など）。

## 仕様（簡易コントラクト）

- 入力
  - `query`（必須）/ `top_k` / `file_type` / `include_documents` / `max_content_length`
- 出力
  - Semche 検索レスポンス（dict）
- エラー
  - 下層の `mcp.semche.search` が送出する例外（`RuntimeError` など）をそのまま伝播

## 利用箇所

- `src/slack_agent/agent.py` の `get_agent_graph()` 内で LangChain の Tool として登録されます。

## 関連ファイルのパス一覧

- 検索実体: `src/slack_agent/mcp/semche.py`
- ツール組み込み: `src/slack_agent/agent.py`