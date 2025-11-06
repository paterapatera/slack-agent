# agent.py の説明

LangChain の Agents API を使用して、OpenAI gpt-4o-mini をバックエンドとするチャットエージェントを初期化・実行します。Slack ハンドラーから呼び出され、ユーザー質問に対する応答テキストを返します。

## 主な関数

- `get_agent_graph() -> Any`
  - `langchain.agents.create_agent` を利用して compiled graph を生成します。
  - モデルは `ChatOpenAI`（`OpenAISettings` から `model`, `api_key` を取得）
  - System プロンプトにより「Slack 向けに簡潔に回答」するよう指示
  - LRU キャッシュでインスタンスを共有し、初期化コストを削減

- `invoke_agent(question: str) -> str`
  - `get_agent_graph()` が返すグラフに対して `ainvoke({"messages": [{"role": "user", "content": question}]})` を実行
  - 返却されたステートの `messages` の最後の `AIMessage` から `content` を抽出して返す
  - エラー時はログ出力後に例外を再送出

## 入出力

- 入力: `question`（ユーザーからの質問テキスト）
- 出力: 文字列の応答テキスト
- 例外: モデル呼び出し障害・ネットワーク障害などの例外をそのまま送出

## 依存

- `langchain`（Agents API `create_agent`）
- `langchain-openai.ChatOpenAI`
- `src/slack_agent/config.OpenAISettings`

## 設計メモ

- Agents API のグラフをキャッシュし、各メッセージ処理での初期化を避けています
- ツールは未登録（将来的に MCP や外部ツールを追加可能）
- Slack ハンドラー側では同期関数内から `asyncio.run(...)` で呼び出します

## コード内で利用しているクラス/関数のパス一覧

- `OpenAISettings`: `src/slack_agent/config.py`
- `ChatOpenAI`: `langchain_openai`
- `create_agent`: `langchain.agents`
