# config.py の説明

このモジュールは Slack の Bot 実行に必要な設定値（トークン）を環境変数から読み込むためのユーティリティを提供します。

## 主な構成要素

- SlackSettings クラス（dataclass）
  - `bot_token`: Bot User OAuth Token（xoxb-...）
  - `app_token`: App Level Token（xapp-...、Socket Mode 用）
  - `from_env()`: `.env` を読み込み（存在すれば）、必須環境変数から `SlackSettings` を構築します。

## 入出力

- 入力: 環境変数 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`
- 出力: `SlackSettings` インスタンス
- エラー: どちらかが未設定の場合 `RuntimeError`

## 依存

- `python-dotenv`: `.env` の読み込みに使用

## コード内で利用しているクラスのファイルパス一覧

- SlackSettings: `src/slack_agent/config.py`
