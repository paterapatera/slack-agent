# config.py の説明

このモジュールは Slack の Bot 実行に必要な設定値（トークン）および OpenAI の設定値を環境変数から読み込むためのユーティリティを提供します。

## 主な構成要素

- SlackSettings クラス（dataclass）
  - `bot_token`: Bot User OAuth Token（xoxb-...）
  - `app_token`: App Level Token（xapp-...、Socket Mode 用）
  - `from_env()`: `.env` を読み込み（存在すれば）、必須環境変数から `SlackSettings` を構築

- OpenAISettings クラス（dataclass）
  - `api_key`: OpenAI API キー（`OPENAI_API_KEY`）
  - `model`: 使用モデル名（`OPENAI_MODEL`、デフォルト: `gpt-5-nano`）
  - `from_env()`: `.env` を読み込み（存在すれば）、必須・任意の環境変数から `OpenAISettings` を構築
  - 備考: コスト配慮のためデフォルトは `gpt-5-nano`。必要に応じて `.env` に `OPENAI_MODEL` を設定して切替可能です。予算上限は OpenAI ダッシュボードの Usage limits で管理してください。

## 入出力

- 入力: 環境変数 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `OPENAI_API_KEY`, `OPENAI_MODEL(任意)`
- 出力: `SlackSettings`, `OpenAISettings` インスタンス
- エラー: 必須が未設定の場合 `RuntimeError`

## 依存

- `python-dotenv`: `.env` の読み込みに使用

## ログ出力・スレッド返信仕様との関連

- 本モジュールは設定の読み出しのみを担当し、ログやスレッド返信の直接制御は行いません。
- ログの初期化は `src/slack_agent/bot.py`、スレッド返信は `src/slack_agent/handlers/message.py` が担当します。

## コード内で利用しているクラスのファイルパス一覧

- SlackSettings: `src/slack_agent/config.py`
- OpenAISettings: `src/slack_agent/config.py`
