# SlackボットのエージェントはSemche MCPを利用できる

## 概要

SlackでBotにメンションされた内容をLangChainエージェントへ渡し、エージェントが必要に応じてSemche MCPサーバーのツールを呼び出して結果を取得し、スレッドで回答します。Semche MCPはコード検索/要約等の機能をMCP（Model Context Protocol）で提供している前提です。

## 実行手順

**必須**: フェーズ内のすべてのタスクにチェックがつくまで、次のフェーズに進まないでください。

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] ストーリーの内容を確認する
- [x] 実現方法を具体化をする
- [x] **実現方法の具体化内容についてユーザーから承認を得る**
- [x] 承認を得た内容をストーリーに反映する

#### 前提・仮定（要確認）

- Semche MCPはMCP仕様に準拠したサーバーで、少なくとも次のツールが利用可能と仮定します（実名・I/Fは要確認）。
  - `semche.search(query: str) -> list[Result]` コード/テキスト検索（本機能で利用するのはこのツールのみ）
  - （参考）`semche.health()` ヘルスチェック等が存在する可能性はあるが、本機能では未使用
- Semche MCPはローカル環境の任意のパスに配置（例: `/path/to/semche`）。
- 接続方式はローカル実行体（stdin/stdout でのMCPセッション、サブプロセス起動）のみを利用する（URL接続は使用しない）。
- 推奨の起動コマンド（例・Semche MCPのワークスペース直下で実行）: `uv run python src/semche/mcp_server.py`
- 認証や接続は環境変数（例: `MCP_SEMCHE_PATH`）で行う。
- BotのLLMはOpenAI gpt-4o-mini（既存方針）を継続利用し、LangChain Agents（`create_agent`）にSemcheツールを渡して、ツール呼び出しはモデルの判断に委ねる。

#### 実現案

**アーキテクチャ概要**

- 既存の `langchain.agents.create_agent` で生成しているエージェントグラフに、Semche MCPのツール（検索/要約）を追加
- ツールはLangChainのBaseTool/Callableとして登録（`langchain_core.tools` の `tool` デコレータ／`StructuredTool` 等）
- ツール実体はMCPクライアントラッパーを経由してSemche MCPサーバーを叩く
- 失敗時はユーザーに分かりやすいメッセージでリトライ/制限案内

**技術スタック**

- LangChain Agents（`create_agent`）
- OpenAI gpt-4o-mini（既存）
- MCPクライアント（Python）: Semche MCPへローカルサブプロセス（stdio）/ または TCP/HTTP/WS 等で接続（クライアント実装は採用するMCPクライアントに依存）

**実装詳細（計画）**

1. 依存関係の追加（検討/仮）
   - `modelcontextprotocol` もしくは適切なMCPクライアント（決定後に確定）
   - 必要に応じて `langchain-community`（ツール補助）

2. 環境変数の追加

   ```
   MCP_SEMCHE_PATH=/path/to/semche          # ローカルMCP実行体/エントリポイントのパス
   MCP_SEMCHE_TIMEOUT=10                    # 例: 秒
   MCP_SEMCHE_API_KEY=...                  # もし必要なら
   # Semche MCP サーバー側が利用するストレージのルート（例: ChromaDB データ）
   SEMCHE_CHROMA_DIR=/path/to/semche/chroma_db
   ```

   備考: `SEMCHE_CHROMA_DIR` はMCPサーバープロセスに渡す必要があります（サブプロセス起動時の環境変数として付与）。

3. 新規モジュールの作成
   - `src/slack_agent/mcp/semche.py`
     - Semche MCPクライアントの薄いラッパー
     - `get_client()` / `search(query: str, top_k: int | None = 5, file_type: str | None = None, include_documents: bool | None = True, max_content_length: int | None = None) -> dict` / （任意）`health()`
   - 例外を`RuntimeError`に正規化して上位で扱いやすく
   - `src/slack_agent/tools/semche.py`
   - LangChainツール定義（`@tool`や`StructuredTool`）
     - Semcheラッパーの `search` を呼び出す（本機能では検索のみツール化）
     - ツール引数は上記検索パラメータに準拠（`query` 必須。他は任意）

4. エージェントの拡張（`src/slack_agent/agent.py`）

- `get_agent_graph()` で `tools=[semche_search_tool]` を渡す
- Systemプロンプトに「必要ならツールを使って最新/正確な情報を取得する」旨を追記

5. エラーハンドリング
   - MCP接続失敗・タイムアウト・4xx/5xx相当の扱い
   - Slackへのユーザーフィードバック文言（リトライ誘導/制限案内）
   - ログ出力（ツール呼び出し引数のPII/秘匿情報はログに残さない）

6. テレメトリ/ログ
   - MCP応答時間・失敗率のメトリクス化（任意）
   - ログレベル/出力量は設定で調整可能に

**受け入れ条件**

- Slackでのメンションに対し、エージェントがSemche MCPツールを利用して結果を含む応答をスレッド返信できる
- MCPサーバーが停止/エラーの場合、ユーザーへ分かりやすいメッセージで通知し、Botが落ちない
- Lint（ruff）/型（mypy）/テスト（pytest）が通る

#### Semche search ツール仕様（本機能で利用）

- 概要: クエリ文字列に対して Dense（ベクトル）と Sparse（BM25）を組み合わせたハイブリッド検索を実行し、RRF で統合した上位件数を返す。
- パラメータ:
  - `query` (string, 必須): 検索クエリ
  - `top_k` (number, 任意, 既定: 5): 取得件数
  - `file_type` (string, 任意): メタデータの file_type でフィルタ
  - `include_documents` (boolean, 任意, 既定: true): 本文を含める
  - `max_content_length` (number, 任意, 既定: None): ドキュメント最大文字数
- 返却値（dict）: `status`, `message`, `results`（`[{ filepath, score, document?, metadata }]`）, `count`, `query_vector_dimension`, `persist_directory`
- 成功例（抜粋）:
  ```json
  {
    "status": "success",
    "message": "ハイブリッド検索が完了しました",
    "results": [
      {
        "filepath": "/docs/dog.txt",
        "score": 0.79,
        "metadata": {
          "file_type": "animal",
          "updated_at": "2025-11-03T12:00:00"
        }
      }
    ],
    "count": 1,
    "query_vector_dimension": null,
    "persist_directory": "./chroma_db"
  }
  ```
- エラー例（抜粋）: `{"status": "error", "message": "...", "error_type": "..."}`

備考:

- 検索対象のドキュメントは、事前に Semche 側のCLI（例: `doc-update`）等でインデックス化しておく必要があります。

#### 参考: MCPクライアント設定例（stdio）

次のようなクライアント設定で、Semche MCPをstdio経由で起動できます。`workspaceFolder` は Semche MCP のワークスペースルートを指します（例: `/path/to/semche`）。

```json
{
  "mcpServers": {
    "semche": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "src/semche/mcp_server.py"],
      "env": {
        "SEMCHE_CHROMA_DIR": "${workspaceFolder}/chroma_db"
      }
    }
  }
}
```

本プロジェクト側でサブプロセスを直接起動する場合も、同等のコマンド・環境変数を用意します（`MCP_SEMCHE_PATH` を基準に `command`/`args` を解決し、`SEMCHE_CHROMA_DIR` を付与）。URL 接続（`MCP_SEMCHE_URL`）は本ストーリーでは使用しません。

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] 依存関係の選定・追加（MCPクライアント）
- [x] 環境変数の定義（`.env.example`追記含む）
- [x] `src/slack_agent/mcp/semche.py` を実装
- [x] `src/slack_agent/tools/semche.py` を実装（LangChainツール）
- [x] `src/slack_agent/agent.py` にツールを組み込み（`create_agent`に渡す）
- [x] エラーハンドリング/ログ調整
- [x] Lint（ruff check . --fix）/ 型チェック（mypy）が通る
- [x] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする
  - AIエージェントが行うので、PRの作成は不要です
- [x] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [x] ツール単体のモックテスト（検索の正常/異常）
- [x] エージェント統合テスト（検索ツール呼び出し経由の応答検証）
- [x] テストが全てパスする

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [ ] 実装内容（`*.exp.md`）を更新する（`mcp/semche.py.exp.md` / `tools/semche.py.exp.md` / `agent.py.exp.md`追記）
- [ ] README.md、AGENTS.md を更新する（MCP設定手順/仕様追記）

### Phase 5: コミット・プッシュ【最終フェーズ】(上から順にチェックしてください)

- [ ] コードのコミットメッセージを作成する
- [ ] **ユーザーからコミットメッセージの承認を受ける**
- [ ] コミット・プッシュする
