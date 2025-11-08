## Slack Agent (Skeleton)

Slack の Bot スケルトンです。Bot がメンションされたとき、LangChain のエージェント（OpenAI gpt-5-nano）で応答を生成し、スレッドに返信します。

## 前提

- Python 3.12+
- Slack App を作成済み（Bot ユーザー有効）
- Socket Mode を有効化済み
- Bot Token Scopes: `app_mentions:read`, `chat:write`, `reactions:write`

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
# OpenAI（gpt-5-nano）
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-5-nano  # 任意（デフォルト: gpt-5-nano）
```

### Slack App 設定手順

1. Slack API で新規 App を作成
2. Bot ユーザーを有効化
3. OAuth & Permissions で以下のスコープを追加
   - `app_mentions:read`
   - `chat:write`
   - `reactions:write`
4. Socket Mode を有効化
5. App Token（`xapp-...`）と Bot Token（`xoxb-...`）を発行
6. `.env` に下記を記載
   - `SLACK_BOT_TOKEN=xoxb-...`
   - `SLACK_APP_TOKEN=xapp-...`
7. App をワークスペースにインストール（スコープ追加後は再インストール）

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

- モデル: `gpt-5-nano`
- 予算管理: OpenAI ダッシュボードの Usage limits で月額上限（例: $10）を設定可能
- プライバシー: API経由のデータは学習に使用されません

### スレッド返信仕様

- Botはメンションイベント受信時、元メッセージの `thread_ts` を参照し、同一スレッド内で返信します。
- スレッド外からメンションされた場合は、そのメッセージを起点に新規スレッドとして返信します。
- **応答生成の前に、受信メッセージへ :eyes: リアクションを付与して「処理中」であることを可視化します。**
  - リアクション付与が失敗しても（`missing_scope` / `already_reacted` / `ratelimited` など）応答処理は継続します。
- 実装は `src/slack_agent/handlers/message.py` の `app_mention` ハンドラで行っています。

### Semche MCP 連携（検索ツール自動ロード）

エージェントは MCP（Model Context Protocol）経由で Semche の検索・リストなどのツール群を **自動ロード** して利用します。初回呼び出し時に stdio 接続でサーバーを起動し、ツール一覧を LangChain Tool に変換して登録します。2 回目以降はキャッシュを使用し再接続しません。

#### 必須/任意の環境変数（`.env`）

| 変数                 | 必須 | 説明                                                                               |
| -------------------- | ---- | ---------------------------------------------------------------------------------- |
| `MCP_SEMCHE_PATH`    | ✅   | Semche リポジトリのルートディレクトリ（例: `/path/to/semche`）。ディレクトリ必須。 |
| `MCP_SEMCHE_TIMEOUT` | 任意 | 接続・ツール取得のタイムアウト秒（デフォルト 10）。                                |
| `SEMCHE_CHROMA_DIR`  | 任意 | Semche サーバプロセスへ引き渡す Chroma DB ディレクトリ。                           |

#### 起動方法（内部）

- `uv run --directory <MCP_SEMCHE_PATH> python src/semche/mcp_server.py` を使用し stdio セッションを開始
- `langchain_mcp_adapters.tools.load_mcp_tools` で MCP 側ツールを LangChain Tool オブジェクトへ変換
- タイムアウトは `safe_timeout = max(1, MCP_SEMCHE_TIMEOUT)` に正規化

#### エラー仕様（フォールバック無し）

| 条件                                                | 例外         | ログメッセージ例                                   |
| --------------------------------------------------- | ------------ | -------------------------------------------------- |
| `MCP_SEMCHE_PATH` 未設定                            | RuntimeError | `MCP_SEMCHE_PATH が未設定`                         |
| `MCP_SEMCHE_PATH` がディレクトリでない              | RuntimeError | `MCP_SEMCHE_PATH はディレクトリを指定してください` |
| サーバスクリプト不存在 (`src/semche/mcp_server.py`) | RuntimeError | `MCP サーバースクリプトが見つかりません`           |
| アダプタ未導入 (`langchain_mcp_adapters`)           | RuntimeError | `langchain_mcp_adapters が見つかりません`          |
| セッション初期化/ツール取得失敗                     | RuntimeError | `MCP ツールの自動ロードに失敗しました`             |
| ツール 0 件                                         | RuntimeError | `MCP から取得できるツールが 0 件でした`            |

フォールバックとして手動定義ツールへ切り替える処理はありません。起動は失敗として扱われます。

#### 注意

- 現状 stdio 接続のみ対応（URL/TCP/WebSocket 未対応）
- 接続はプロセス内で 1 回のみ行われます（メモ化）

内部実装の詳細は `src/slack_agent/agent.py.exp.md` を参照してください。

### （任意）開発ツールの導入例

```zsh
# 開発用ツールを dev 依存に追加
uv add --dev ruff mypy

# 実行
uv run ruff check . --fix
uv run mypy src
```

## テスト・静的解析の実行方法

### テスト（pytest）

```zsh
uv run pytest
```

### Lint（ruff）

```zsh
uv run ruff check . --fix
```

### 型チェック（mypy）

```zsh
uv run mypy src
```
