# mcp/semche.py の説明

Semche MCP サーバー（ローカル stdio 接続）に対する薄いクライアントラッパーを提供します。本モジュールは「検索（search）」機能のみを公開し、LangChain ツール層から呼び出されます。

## 主な構成・関数

- `SemcheClientSettings`
  - `.from_env()` で以下の環境変数を読み込みます。
    - `MCP_SEMCHE_PATH`（必須・サーバールートパス。例: `/path/to/semche`）
    - `MCP_SEMCHE_TIMEOUT`（任意・秒数。例: `10`）
    - `SEMCHE_CHROMA_DIR`（任意・サーバー側の ChromaDB ルート）
    - `SEMCHE_MOCK`（任意・`1` ならモック応答）

- `get_client()`
  - stdio（`uv run python src/semche/mcp_server.py`）で MCP セッションを起動し、クライアントを生成して返します。
  - 実接続が行えない場合や `SEMCHE_MOCK=1` の場合は、モックモードの利用を上位に通知します。

- `search(query: str, top_k: int | None = 5, file_type: str | None = None, include_documents: bool | None = True, max_content_length: int | None = None) -> dict`
  - Semche MCP の `search` ツールを呼び出し、以下のスキーマの dict を返します。
  - 返却スキーマ: `status`, `message`, `results`, `count`, `query_vector_dimension`, `persist_directory`
  - 失敗時は `RuntimeError` を送出します。

## 仕様（簡易コントラクト）

- 入力
  - `query`: 検索クエリ（必須）
  - `top_k`: ヒット上位件数（既定 5）
  - `file_type`: メタデータでの絞り込み
  - `include_documents`: 本文を含めるか（既定 True）
  - `max_content_length`: 本文の最大長
- 出力
  - Semche 検索レスポンス（dict）。`status == "success"` 時に `results` を参照可能
- エラー
  - 接続・タイムアウト・ツールエラー時は `RuntimeError`

## 環境変数

- `MCP_SEMCHE_PATH`: Semche MCP ワークスペースのパス
- `MCP_SEMCHE_TIMEOUT`: タイムアウト秒（例: 10）
- `SEMCHE_CHROMA_DIR`: サーバー内で使用する ChromaDB の永続ディレクトリ
- `SEMCHE_MOCK`: `1` でモック応答に切替（開発・CI 向け）

## 依存/関連ファイルのパス一覧

- 呼び出し元ツール: `src/slack_agent/tools/semche.py`
- エージェント組み込み: `src/slack_agent/agent.py`
- OpenAI 設定: `src/slack_agent/config.py`
