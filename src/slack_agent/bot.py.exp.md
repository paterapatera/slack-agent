# bot.py の説明

Slack Bolt アプリケーションを構築し Socket Mode で起動するエントリポイントです。

## 主な構成

- `build_app()`: 環境変数からトークンを読み込み `App` を生成し、ハンドラー登録を行う。
- `main()`: `SocketModeHandler` を使ってアプリを開始。

## ログ出力とスレッド返信との関係

- `main()` の冒頭で `logging.basicConfig(level=INFO, format=...)` を設定し、以降のモジュール（例: `handlers.message`, `agent`）のログを集約します。
- スレッドへの返信そのものは `handlers/message.py` 側で `say(..., thread_ts=...)` により実施されます。本モジュールは起動とログ初期化を担当します。

## 依存

- `SlackSettings`: `src/slack_agent/config.py`
- `message.register`: `src/slack_agent/handlers/message.py`
- `slack_bolt.App`
- `slack_bolt.adapter.socket_mode.SocketModeHandler`

## 入出力

- 入力: 環境変数 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`
- 出力: Slack Socket Mode の起動（WebSocket 接続）

## コード内で利用しているクラスのモジュールパス一覧

- `App`: `slack_bolt`
- `SocketModeHandler`: `slack_bolt.adapter.socket_mode`
- `SlackSettings`: `src/slack_agent/config.py`
