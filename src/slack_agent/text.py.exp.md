# text.py の説明

Slackメッセージの先頭メンション（`<@U...>`）を除去し、残りのテキストを整形する関数 `clean_mention_text` を提供します。

## 主な関数

- `clean_mention_text(text: str) -> str`
  - 先頭メンション（`<@U...>`）とその前後の空白を除去し、残りのテキストを返します。
  - テキストが空、またはメンション以外何も残らない場合は `(no message)` を返します。
  - 先頭にメンションがない場合はトリミングのみ行います。

## 入出力

- 入力: Slackメッセージテキスト（str）
- 出力: 整形済みテキスト（str）

## 利用箇所

- `src/slack_agent/handlers/message.py` の `handle_app_mention` 内で、受信テキストの整形に使用

## コード内で利用しているクラス・関数のファイルパス一覧

- re.Pattern: 標準ライブラリ re
- DEFAULT_EMPTY_MESSAGE: `src/slack_agent/text.py`

## 備考

- テストは `tests/test_text.py` で実施
