# agent.py の説明

LangChain Agents API（`create_agent`）を用いて、Slack 応答用のエージェントグラフを構築・呼び出すモジュールです。OpenAI LLM を利用し、MCP（Model Context Protocol）経由で動的にツールを自動ロードして、エージェントに登録します。

## 主な関数

### `MCPConnectionManager` シングルトン

- 永続 MCP セッション（stdio + `ClientSession`）をプロセス内で 1 度だけ開始し保持。
- `ensure_started()` が初期化を担当（環境変数/パス検証→サーバ起動→`ClientSession.initialize()`）。
- `close()` で安全にクローズ。`atexit` 登録によりプロセス終了時も自動クローズ。失敗しても握りつぶし。
- ツールはマネージャ内部にもキャッシュ（`set_tools`/`get_tools`）。モジュールレベル `_cached_tools` と二重で保持し互換性維持。
- 途中失敗時は `_safe_close()` により中途リソースを解放し、再試行可能な状態に戻す。

### `load_mcp_tools_once() -> list[Any]` (非同期)

- MCPConnectionManager が開始した永続セッションから LangChain Tool 群を 1 回だけロード。
- **メモ化**: `_cached_tools` + `_tools_lock`。再呼び出し時は永続セッションを再利用し再接続不要。
- **接続先/起動方法**:
  - `MCP_SEMCHE_PATH`: Semche リポジトリのディレクトリ必須。存在/ディレクトリ性/`src/semche/mcp_server.py` の有無を検証。
  - 起動: `uv run --directory <MCP_SEMCHE_PATH> python src/semche/mcp_server.py`（stdioのみ対応、フォールバック無し）。
  - 環境: `SEMCHE_CHROMA_DIR` があれば子プロセスへ継承。
  - タイムアウト: `MCP_SEMCHE_TIMEOUT` 正規化 (`safe_timeout=max(1, raw)`)。
- **依存**: `langchain_mcp_adapters.tools.load_mcp_tools`。未導入/Import失敗→`RuntimeError`。
- **エラー仕様**:
  - `MCP_SEMCHE_PATH` 未設定 / 非ディレクトリ / スクリプト不存在 → `RuntimeError`
  - アダプタ未導入 → `RuntimeError`
  - 初期化失敗（timeout 等）→ `RuntimeError`
  - ツール 0 件 → `RuntimeError`
  - いずれもフォールバック無し。成功時のみ利用。
  - 部分的初期化失敗時はセッションをクリーンアップし再試行可。

### `get_agent_graph() -> Any` (非同期)

- OpenAI 設定を `OpenAISettings.from_env()` から取得し、`ChatOpenAI` を初期化。
- System プロンプトを「Slack 向けに簡潔に回答し、必要に応じて MCP ツールを利用する」方針で設定。
- `load_mcp_tools_once()` でツール群を取得しエージェントに登録（失敗時は例外が伝播し起動失敗）。
- エージェントグラフを生成して返します（`_agent_lock` と `_agent_graph` によるメモ化で 1 インスタンスをキャッシュ）。

### `invoke_agent(question: str) -> str` (非同期)

- `get_agent_graph()` でエージェントグラフを取得し、`ainvoke` で `{"messages": [{"role": "user", "content": question}]}` を渡して実行。
- 返却された `state["messages"]` の末尾が `AIMessage` であれば `content` を取り出し、文字列で返します。
- 例外はログ出力の上で再送出します。

## 仕様（簡易コントラクト）

- 入力
  - `question: str`（Slack からのメッセージ本文。mentions は `clean_mention_text` 側で除去済み）
- 出力
  - `str`（最終的に Slack へ返信する本文）
- エラー
  - MCP 初期化失敗、LLM やツール呼び出しで失敗した場合は例外を送出し、呼び出し元でハンドリング

## MCP ツール自動ロードフロー

1. 初回 `load_mcp_tools_once()` が `_mcp_manager.ensure_started()` を呼び永続セッション確立。
2. `ClientSession.initialize()` 完了後、`load_mcp_tools(session)` を実行して LangChain Tool 群取得。
3. ツールを `_mcp_manager` と `_cached_tools` にキャッシュ。
4. `get_agent_graph()` がツールを受け取りエージェント構築。
5. 2 回目以降はセッション再接続なしでキャッシュ済みツール/グラフを返す。
6. プロセス終了時 `atexit` でセッション/stdio を順次クローズ（ベストエフォート）。

## 失敗時のエラー仕様（再整理）

| ケース           | 条件                                          | 例外         | ログキーワード             |
| ---------------- | --------------------------------------------- | ------------ | -------------------------- |
| 環境未設定       | `MCP_SEMCHE_PATH` 空                          | RuntimeError | "未設定"                   |
| パス不正         | 非ディレクトリ                                | RuntimeError | "ディレクトリ"             |
| スクリプト不存在 | `src/semche/mcp_server.py` 無し               | RuntimeError | "見つかりません"           |
| アダプタ未導入   | import 失敗                                   | RuntimeError | "見つかりません"           |
| 初期化失敗       | timeout / 読み書きエラー                      | RuntimeError | "自動ロード中に失敗"       |
| ツール 0 件      | load_mcp_tools が空                           | RuntimeError | "0 件"                     |
| 部分失敗後再試行 | `_safe_close()` 実行→再度 ensure_started 可能 | -            | "safe_close" (DEBUG/ERROR) |

フォールバックは一切提供しない設計。失敗時は上流（Slack ハンドラ）で例外として通知/ログ。

## ログ出力／スレッド返信仕様との関係

- エージェントの生成・呼び出しは `INFO` ログを出力（モデル名、ツール件数など）
- MCP ツールのロード失敗は `ERROR` ログ
- スレッド返信自体は `handlers/message.py` 側で `thread_ts` を指定して行います（本モジュールは本文生成に専念）

## コード内で利用しているクラス・関数のファイルパス一覧

- `OpenAISettings`: `src/slack_agent/config.py`
- `ChatOpenAI`: `langchain_openai`
- `create_agent`: `langchain.agents`
- `AIMessage`: `langchain_core.messages`
- `ClientSession`, `stdio_client`, `StdioServerParameters`: `mcp` / `mcp.client.stdio`
- `load_mcp_tools` (遅延 import): `langchain_mcp_adapters.tools`
