# handlers/message.py の説明

`app_mention` イベントを処理するハンドラーを登録します。Bot がメンションされた際、メッセージの先頭のメンション（`<@U...>`）を取り除き、残りのテキストを LangChain のエージェント（OpenAI gpt-4o-mini）に渡して応答を生成し、スレッドに返信します。テキストが空の場合は `(no message)` が渡されます。

## 主な関数

返信時は `thread_ts` を指定し、元メッセージのスレッド内に返信します。
スレッド外からメンションされた場合は、そのメッセージを起点に新規スレッドとして返信します。

- `register(app: App) -> None`
  - 渡された `App` に対して `app_mention` イベントハンドラーを登録します。受信テキストを整形後、`slack_agent.agent.invoke_agent()` を呼び出して応答を取得し、スレッドに返信します。

## 入出力

- 入力: Slack イベントペイロード（`event`）、`say`
- 出力: エージェントの応答テキスト、スレッド内返信（thread_ts指定）

## コード内で利用しているクラスのモジュールパス一覧

- `App`: `slack_bolt`
- `Say`: `slack_bolt.context.say.say`
- `invoke_agent`: `src/slack_agent/agent.py`

## 依存

- `slack_bolt.App`
- `slack_bolt.context.say.say.Say`
- `src/slack_agent/text.clean_mention_text`（メンション除去・テキスト整形）
- `src/slack_agent/agent.invoke_agent`（LLM呼び出し）

## clean_mention_text 関数の利用箇所・仕様

- 利用箇所: `handle_app_mention` 内で、受信テキストの整形に使用
- 仕様: 先頭メンション（`<@U...>`）除去・空白トリム・空なら `(no message)` 返却
- 実装: `src/slack_agent/text.py` に定義
