# MCPツール自動ロード拡張

## 概要

LangChain MCPアダプタを用いて、MCPセッションから利用可能なツールを自動的に読み込み、エージェントに登録する仕組みを導入します。これにより、Semche以外のMCP（今後追加予定）も最小変更で取り込めるようにします。

## 実行手順

**必須**: フェーズ内のすべてのタスクにチェックがつくまで、次のフェーズに進まないでください。

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] ストーリーの内容を確認する
- [x] 実現方法を具体化をする
- [x] **実現方法の具体化内容についてユーザーから承認を得る**
- [x] 承認を得た内容をストーリーに反映する

#### 実現案

以下の方針で進めます。ご確認ください（承認後に実装へ進みます）。

1. MCPツールの自動ロード
   - `mcp.client.stdio.stdio_client` + `mcp.ClientSession` で stdio 経由の MCP セッションを初期化
     - 既存の `MCP_SEMCHE_PATH`/`SEMCHE_CHROMA_DIR`/`MCP_SEMCHE_TIMEOUT` を尊重（`src/slack_agent/mcp/semche.py` と同等の環境変数）
   - `langchain_mcp_adapters.tools.load_mcp_tools(session)` を優先的に使用し、LangChain の Tool 配列を取得
   - アダプタ未導入やセッション初期化/ツール取得に失敗した場合は「エラーとする」（手動Semcheフォールバックは行わない）

2. 非同期初期化とメモ化
   - `async def load_mcp_tools_once() -> list[Any]` を実装（場所: `src/slack_agent/agent.py` 内にまず実装。必要なら将来 `mcp/loader.py` に抽出）
   - モジュールスコープに `asyncio.Lock` と `_cached_tools: list[Any] | None` を持ち、一度だけ接続・ロード
   - タイムアウト・例外・ツール0件時は、状況に応じたメッセージで `RuntimeError` を送出（ログも出力）

3. Agent 構築の非同期化（フォールバックなし）
   - `get_agent_graph()` を `async def get_agent_graph()` に変更し、最初の呼び出しで一度だけ `create_agent` を構築・キャッシュ
   - ツールは `await load_mcp_tools_once()` の結果をそのまま使用（失敗時は例外が伝播し、起動失敗とする）
   - System プロンプトや LLM 設定（`OpenAISettings`）は現状を踏襲

4. 依存関係と互換性
   - 依存追加: `langchain_mcp_adapters`（名称は実パッケージに合わせて確定）。インポートは try/except でラップし、未導入なら明確なエラーを出す
   - 既存の `mcp` 依存は継続利用
   - mypy は `ignore_missing_imports = true`

5. エラーハンドリング/ログ
   - 代表的なエラー: セッション確立失敗、`list_tools` 失敗、タイムアウト、ツール0件、アダプタ未導入
   - これらは `logger.warning/info/error` を適切に出しつつ `RuntimeError` を送出（フォールバックなし）
   - 将来の拡張でリトライ/バックオフを検討（今回は単純化）

6. テスト観点（実装後に追加）
   - 自動ロード成功（アダプタ import 可能かつモックセッションで Tool が取得できるパス）
   - 自動ロード失敗時に例外が送出されること（手動ツールへは切り替えない）
   - `load_mcp_tools_once` が一度しかセッション初期化を行わないこと（メモ化）

7. 追加の設計メモ
   - 現時点では Semche 1種を stdio 接続。将来的に別 MCP を増やす場合、セッションを配列で持ち、各セッションのツール群を合成して渡す実装に拡張
   - セキュリティ上、外部コマンド起動の引数・環境変数はログに生で出さない

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] `agent.py` を非同期初期化対応（`async def get_agent_graph()`）へ変更
- [x] MCPツール自動ロード関数 `async def load_mcp_tools_once()` を実装（メモ化/ロック）
- [x] 自動ロード結果が0件/失敗時は `RuntimeError` を送出する（フォールバック無し）
- [x] Lint（ruff check . --fix）/ 型チェック（mypy）が通る
- [x] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする
  - AIエージェントが行うので、PRの作成は不要です
- [x] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [x] 自動ロード成功: `load_mcp_tools_once` が呼ばれ Tool が登録される
- [x] 自動ロード失敗: 例外（`RuntimeError`）が送出される
- [x] セッション初期化一度きり（メモ化）が担保される

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [x] `agent.py.exp.md` に自動ロードフローと失敗時のエラー仕様を追記
- [x] README.md に環境変数・起動手順・依存関係を追記
- [x] AGENTS.md に本ストーリーの方針と決定を記録

### Phase 5: コミット・プッシュ【最終フェーズ】(上から順にチェックしてください)

- [ ] コードのコミットメッセージを作成する
- [ ] **ユーザーからコミットメッセージの承認を受ける**
- ストーリーにチェック後にコミット・プッシュする

## 追加要件・前提

- 依存関係として `langchain_mcp_adapters`（または同等のMCP→LangChainブリッジ）を導入。
- stdio接続（`MCP_*_PATH`）を基本とし、将来HTTP接続にも対応可能な抽象化を検討。
- 自動ロードは「Agentのツール選択裁量」を前提とし、ツール使用判断はAgentに委譲。
