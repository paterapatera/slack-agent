## Slack Agent (Skeleton)

Slack の Bot スケルトンです。Bot がメンションされたとき、LangChain のエージェント（OpenAI gpt-4o-mini）で応答を生成し、スレッドに返信します。

## 前提

- Python 3.12+
- Slack App を作成済み（Bot ユーザー有効）
- Socket Mode を有効化済み
- Bot Token Scopes: `app_mentions:read`, `chat:write`

## セットアップ（uv）

1. 依存のインストール

```zsh
# プロジェクト直下で依存を同期（.venv が自動作成されます）
uv sync
```

2. 環境変数の設定

`.env.example` を `.env` にコピーし、値を設定します。

```zsh
cp .env.example .env
# .env を編集して以下を設定
# Slack
#   SLACK_BOT_TOKEN=xoxb-...
#   SLACK_APP_TOKEN=xapp-...
# OpenAI（gpt-4o-mini）
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-4o-mini  # 任意（デフォルト: gpt-4o-mini）
```

### Slack App 設定手順

1. Slack API で新規 App を作成
2. Bot ユーザーを有効化
3. OAuth & Permissions で以下のスコープを追加
   - `app_mentions:read`
   - `chat:write`
4. Socket Mode を有効化
5. App Token（`xapp-...`）と Bot Token（`xoxb-...`）を発行
6. `.env` に下記を記載
   - `SLACK_BOT_TOKEN=xoxb-...`
   - `SLACK_APP_TOKEN=xapp-...`
7. App をワークスペースにインストール

## 実行

エントリポイントは `slack_agent.bot:main` です。

```zsh
# プロジェクト環境でコマンド実行
uv run slack-agent
# もしくは
uv run -m slack_agent.bot
```

起動後、Slack で Bot にメンションしてメッセージを送ると、エージェントの応答がスレッドで返ります。

### OpenAI 利用について

- モデル: `gpt-4o-mini`
- 予算管理: OpenAI ダッシュボードの Usage limits で月額上限（例: $10）を設定可能
- プライバシー: API経由のデータは学習に使用されません

### スレッド返信仕様

- Botはメンションイベント受信時、元メッセージの `thread_ts` を参照し、同一スレッド内で返信します。
- スレッド外からメンションされた場合は、そのメッセージを起点に新規スレッドとして返信します。
- 実装は `src/slack_agent/handlers/message.py` の `app_mention` ハンドラで行っています。

### Semche MCP 連携（検索ツール）

本プロジェクトのエージェントは、必要に応じて Semche MCP の検索ツールを呼び出せます（ローカル stdio 接続のみ想定）。

- 前提
   - Semche MCP のワークスペースがローカルにある（例: `/path/to/semche`）
   - Semche 側の検索対象ドキュメントは事前にインデックス化済み
- サーバー起動（参考）
   - ワークスペース直下で次を実行: `uv run python src/semche/mcp_server.py`
- プロジェクト側の環境変数（`.env`）
   - `MCP_SEMCHE_PATH=/path/to/semche`  # 必須（サーバーのワークスペースパス）
   - `MCP_SEMCHE_TIMEOUT=10`           # 任意（秒）
   - `SEMCHE_CHROMA_DIR=/path/to/semche/chroma_db`  # 任意（サーバーに引き渡す）
   - `SEMCHE_MOCK=1`                  # 任意（開発/CI向けのモック応答）

注意: 本プロジェクトは stdio のみ対応（URL/TCP/WS は未対応）。

内部実装の概要は `src/slack_agent/mcp/semche.py.exp.md` および `src/slack_agent/tools/semche.py.exp.md` を参照してください。

### （任意）開発ツールの導入例

```zsh
# 開発用ツールを dev 依存に追加
uv add --dev ruff mypy

# 実行
uv run ruff check .
uv run mypy src
```

## テスト・静的解析の実行方法

### テスト（pytest）

```zsh
uv run pytest
```

### Lint（ruff）

```zsh
uv run ruff check .
```

### 型チェック（mypy）

```zsh
uv run mypy src
```
