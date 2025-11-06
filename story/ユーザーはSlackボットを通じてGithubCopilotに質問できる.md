# ユーザーはSlackボットを通じてGithubCopilotに質問できる

## 概要

ユーザーがSlackでボットにメンション付きメッセージを送信すると、GitHub Copilotに質問が転送され、Copilotからの回答をSlackのスレッドで受け取ることができる機能を実装します。

## 実行手順

**必須**: フェーズ内のすべてのタスクにチェックがつくまで、次のフェーズに進まないでください。

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] ストーリーの内容を確認する
- [x] 実現方法を具体化をする
- [x] **実現方法の具体化内容についてユーザーから承認を得る**
- [x] 承認を得た内容をストーリーに反映する

#### 実現案

**アーキテクチャ概要**

LangChainのエージェント機能を使用し、OpenAI gpt-4o-miniをLLMとして統合します。将来的にはMCP（Model Context Protocol）にも対応できる設計にします。

**技術スタック**

- **LangChain**: エージェント機能、LLM統合フレームワーク
- **OpenAI API (gpt-4o-mini)**: LLMプロバイダー
- **予算管理**: 月$10の上限設定

**実装詳細**

1. **依存関係の追加**
   - `langchain-core`: LangChainコアライブラリ
   - `langchain-openai`: OpenAI統合パッケージ
   - `langchain-community`: （将来のMCP対応用）

2. **環境変数の追加**

   ```
   OPENAI_API_KEY=sk-xxx  # OpenAI APIキー
   OPENAI_MODEL=gpt-4o-mini  # 使用するモデル（デフォルト）
   ```

3. **新規モジュールの作成**
   - `src/slack_agent/agent.py`: LangChainエージェントの初期化・実行ロジック
     - `ChatOpenAI`をLLMとして設定（gpt-4o-mini）
     - エージェント構築（将来的にツール追加可能）
     - 将来のMCP対応を考慮した設計

4. **メッセージハンドラーの修正** (`src/slack_agent/handlers/message.py`)
   - `clean_mention_text`でメンション除去
   - `agent.py`のエージェント実行関数を呼び出し
   - エージェントの応答をSlackスレッドに返信
   - エラーハンドリング（API障害、タイムアウト、レート制限など）

5. **設定の拡張** (`src/slack_agent/config.py`)
   - `OpenAISettings`クラスを追加
   - OpenAI APIキー、モデル名の管理
   - 将来のMCP設定も追加可能な構造

6. **エラーハンドリング**
   - API呼び出しエラー（認証失敗、ネットワークエラー）
   - レート制限エラー（429エラー）
   - タイムアウト
   - ユーザーフレンドリーなエラーメッセージをSlackに返信

7. **MCP対応の準備**
   - エージェントのツール追加インターフェースを設計
   - 設定ファイルでMCPサーバー情報を管理できる構造を用意

**OpenAI API キーの取得手順**

1. OpenAI Platform（https://platform.openai.com/）にアクセス
2. API Keysセクションで新しいAPIキーを作成
3. `.env`ファイルに`OPENAI_API_KEY`を保存
4. Usage limits で月$10の上限を設定（推奨）
   - Settings → Limits → Usage limits で設定可能
   - 上限に達するとAPI呼び出しが自動停止

**予算管理**

- **月額上限**: $10（OpenAIダッシュボードで設定）
- **想定利用量**:
  - 小規模チーム（5人）: 月1,500-3,000質問 → $2-3
  - 個人利用: 月600-900質問 → $0.6-$1.5
- **料金**:
  - 入力: $0.15 / 1Mトークン
  - 出力: $0.60 / 1Mトークン

**使用するモデル**

- **gpt-4o-mini**: 高速・安価・高品質なバランス型モデル
- APIデータは学習に使用されない（OpenAI ポリシー）

**将来のMCP対応**

- LangChainのツール機構を使ってMCPサーバーと連携
- `agent.py`でMCPクライアントを初期化し、ツールとして登録
- 設定ファイルでMCPサーバーのエンドポイントを管理

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] OpenAI APIキーを取得し、環境変数に設定する
- [x] 依存関係を追加する（langchain-core, langchain-openai, langchain）
- [x] OpenAISettings を config.py に追加する
- [x] agent.py を作成し、LangChainエージェントを実装する（Agents API: create_agent）
- [x] メッセージハンドラーにエージェント呼び出し処理を追加する
- [x] エラーハンドリングを実装する
- [x] Lint（ruff check . --fix）/ 型チェック（mypy）が通る
- [x] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする
  - AIエージェントが行うので、PRの作成は不要です
- [x] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [x] テストコードを作成する（`tests/test_agent.py`）
- [x] テストが全てパスする（pytest / pytest-asyncio）

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [x] 実装内容（`*.exp.md`）を更新する（agent.py.exp.md 追加、message.py.exp.md / config.py.exp.md 更新）
- [x] README.md、AGENTS.md を更新する（OpenAI設定・Agents API 反映）

### Phase 5: コミット・プッシュ【最終フェーズ】(上から順にチェックしてください)

- [ ] コードのコミットメッセージを作成する
- [ ] **ユーザーからコミットメッセージの承認を受ける**
- [ ] コミット・プッシュする
