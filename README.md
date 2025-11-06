## Slack Agent (Skeleton)

Slack の Bot スケルトンです。Bot がメンションされたとき、`hello {受け取ったメッセージ}` を返します。

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
# .env を編集して SLACK_BOT_TOKEN, SLACK_APP_TOKEN を設定
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

起動後、Slack で Bot にメンションしてメッセージを送ると、`hello {受け取ったメッセージ}` と返信されます。

### スレッド返信仕様

- Botはメンションイベント受信時、元メッセージの `thread_ts` を参照し、同一スレッド内で返信します。
- スレッド外からメンションされた場合は、そのメッセージを起点に新規スレッドとして返信します。
- 実装は `src/slack_agent/handlers/message.py` の `app_mention` ハンドラで行っています。

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
