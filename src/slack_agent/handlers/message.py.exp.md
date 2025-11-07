# handlers/message.py の説明

`app_mention` イベントを処理するハンドラーを登録します。Bot がメンションされた際、メッセージの先頭のメンション（`<@U...>`）を取り除き、残りのテキストを LangChain のエージェント（OpenAI gpt-5-nano）に渡して応答を生成し、スレッドに返信します。テキストが空の場合は `(no message)` が渡されます。さらに応答生成に入る前に対象メッセージへ `:eyes:` リアクションを付与し、ユーザーへ「処理中」であることを即時にフィードバックします。リアクション付与が失敗しても（`missing_scope` / `already_reacted` / `ratelimited` / 想定外エラー）本処理は継続されます。

## 主な関数

返信時は `thread_ts` を指定し、元メッセージのスレッド内に返信します。
スレッド外からメンションされた場合は、そのメッセージを起点に新規スレッドとして返信します。

- `register(app: App) -> None`
  - 渡された `App` に対して `app_mention` イベントハンドラーを登録します。受信テキストを整形後、応答生成前に `:eyes:` リアクション追加（`_try_add_eyes_reaction`）を試み、続いて `slack_agent.agent.invoke_agent()` を呼び出して応答を取得し、スレッドに返信します。
- `_try_add_eyes_reaction(app: App, event: Mapping[str, Any]) -> None`
  - 内部ヘルパー。`channel` と `ts` が存在すれば `reactions.add` API を呼び出して `:eyes:` を付与。SlackApiError のエラーコード別にログレベルを調整し、失敗しても例外を外へ伝播しない。

## 入出力

- 入力: Slack イベントペイロード（`event`）、`say`
- 出力: エージェントの応答テキスト、スレッド内返信（thread_ts指定）

## コード内で利用しているクラス/関数のモジュールパス一覧

- `App`: `slack_bolt`
- `Say`: `slack_bolt.context.say.say`
- `invoke_agent`: `src/slack_agent/agent.py`
- `SlackApiError`: `slack_sdk.errors`（フォールバック定義あり）
- `clean_mention_text`: `src/slack_agent/text.py`

## 依存

- `slack_bolt.App`
- `slack_bolt.context.say.say.Say`
- `slack_sdk.errors.SlackApiError`（リアクション付与のエラーハンドリング）
- `src/slack_agent/text.clean_mention_text`（メンション除去・テキスト整形）
- `src/slack_agent/agent.invoke_agent`（LLM呼び出し）

## clean_mention_text 関数の利用箇所・仕様

- 利用箇所: `handle_app_mention` 内で、受信テキストの整形に使用
- 仕様: 先頭メンション（`<@U...>`）除去・空白トリム・空なら `(no message)` 返却
- 実装: `src/slack_agent/text.py` に定義

## :eyes: リアクション付与仕様

- 目的: 応答生成開始前の「処理中」可視化
- API: `reactions.add` (`name="eyes"`)
- 成功時: INFO ログを出力
- 代表的エラーコードと扱い:
  - `already_reacted`: INFO ログ（成功相当）
  - `missing_scope`: WARNING ログ（スコープ不足、処理継続）
  - `ratelimited`: WARNING ログ（レート制限、処理継続）
  - その他: WARNING ログ
- 想定外例外: WARNING ログ、処理継続
- フォールバック: `SlackApiError` がインポートできない環境でも簡易クラス定義で継続
