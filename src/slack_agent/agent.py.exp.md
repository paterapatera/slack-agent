# agent.py の説明

LangChain Agents API（`create_agent`）を用いて、Slack 応答用のエージェントグラフを構築・呼び出すモジュールです。OpenAI LLM を利用し、MCP（Model Context Protocol）経由で動的にツールを自動ロードして、エージェントに登録します。

## 主な関数

### `load_mcp_tools_once() -> list[Any]` (非同期)

- MCP セッションから LangChain Tool 群を一度だけ自動ロードして返します。
- **メモ化**: モジュールスコープの `_cached_tools` と `asyncio.Lock` により、プロセス内で一度だけ初期化・接続を行い、以降はキャッシュを返します。
- **接続先/起動方法**:
  - `MCP_SEMCHE_PATH` は Semche リポジトリの「ルートディレクトリ」を必須とする（ファイルパス指定は不可）。
  - サーバスクリプトは `<MCP_SEMCHE_PATH>/src/semche/mcp_server.py` を想定し、存在しなければ `RuntimeError`。
  - stdio 接続は `StdioServerParameters` で `uv run --directory <MCP_SEMCHE_PATH> python src/semche/mcp_server.py` を実行して確立する。
  - `SEMCHE_CHROMA_DIR` は子プロセス環境に引き継がれる。
  - タイムアウトは `MCP_SEMCHE_TIMEOUT`（秒、デフォルト 10）。内部では `safe_timeout = max(1, timeout)` に正規化して使用。
- **依存**: `langchain_mcp_adapters.tools.load_mcp_tools` を使用してツールを変換。未導入時は `RuntimeError`。
- **エラー仕様**:
  - `MCP_SEMCHE_PATH` 未設定 → `RuntimeError`
  - `MCP_SEMCHE_PATH` がディレクトリでない → `RuntimeError`
  - サーバスクリプト（`src/semche/mcp_server.py`）が存在しない → `RuntimeError`
  - アダプタ未導入 → `RuntimeError`
  - セッション初期化失敗 / ツール 0 件 → `RuntimeError`
  - フォールバック無し（エラー時は起動失敗）

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

1. 初回 `get_agent_graph()` 呼び出し時に `load_mcp_tools_once()` を実行
2. `langchain_mcp_adapters` が利用可能であれば、以下で stdio セッションを初期化

- `uv run --directory <MCP_SEMCHE_PATH> python src/semche/mcp_server.py`
- `ClientSession.initialize()` を `safe_timeout` で待機

3. `load_mcp_tools(session)` で LangChain Tool 群へ変換
4. 取得したツールをエージェントに登録
5. 2 回目以降はキャッシュを返す（再接続なし）

## 失敗時のエラー仕様

- **アダプタ未導入**: `langchain_mcp_adapters` が import できない → `RuntimeError`（ログに `"langchain_mcp_adapters が見つかりません"`）
- **環境変数未設定**: `MCP_SEMCHE_PATH` が空 → `RuntimeError`（ログに `"MCP_SEMCHE_PATH が未設定"`）
- **セッション初期化失敗**: タイムアウト / 接続エラー → `RuntimeError`（ログに `"MCP ツールの自動ロード中に失敗しました"`）
- **ツール 0 件**: `load_mcp_tools` が空リストを返した → `RuntimeError`（ログに `"MCP から取得できるツールが 0 件でした"`）
- フォールバック無し: 手動ツール定義（Semche ラップ）への切り替えは行わず、起動失敗とする

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
