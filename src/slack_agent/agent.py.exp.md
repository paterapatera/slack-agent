# agent.py の説明

LangChain Agents API（`create_agent`）を用いて、Slack 応答用のエージェントグラフを構築・呼び出すモジュールです。OpenAI gpt-4o-mini を利用し、必要に応じて Semche の検索ツールを呼び出せるようにツールを登録します。

## 主な関数

- `get_agent_graph() -> Any`
  - OpenAI 設定を `OpenAISettings.from_env()` から取得し、`ChatOpenAI` を初期化。
  - System プロンプトを「Slack 向けに簡潔に回答する」方針で設定。
  - `slack_agent.tools.semche.semche_search` を LangChain の `Tool` として包み、エージェントに登録（利用不可な環境ではツール無しのフォールバック）。
  - エージェントグラフを生成して返します（`@lru_cache` により 1 インスタンスをキャッシュ）。

- `invoke_agent(question: str) -> str`
  - `get_agent_graph()` でエージェントグラフを取得し、`ainvoke` で `{"messages": [{"role": "user", "content": question}]}` を渡して実行。
  - 返却された `state["messages"]` の末尾が `AIMessage` であれば `content` を取り出し、文字列で返します。
  - 例外はログ出力の上で再送出します。

## 仕様（簡易コントラクト）

- 入力
  - `question: str`（Slack からのメッセージ本文。mentions は `clean_mention_text` 側で除去済み）
- 出力
  - `str`（最終的に Slack へ返信する本文）
- エラー
  - LLM やツール呼び出しで失敗した場合は例外を送出し、呼び出し元でハンドリング

## Semche ツール連携

- `semche_search(query: str, top_k: int|None, file_type: str|None, include_documents: bool|None, max_content_length: int|None)` を `Tool` 化して登録します。
- 返却値は Semche の返却スキーマ（`status`, `message`, `results`, `count`, `query_vector_dimension`, `persist_directory`）。
- 依存関係
  - `src/slack_agent/tools/semche.py`（ツールラッパ）
  - `src/slack_agent/mcp/semche.py`（MCP クライアント。stdio のみ対応）

## ログ出力／スレッド返信仕様との関係

- エージェントの生成・呼び出しは `INFO` ログを出力（モデル名など）
- スレッド返信自体は `handlers/message.py` 側で `thread_ts` を指定して行います（本モジュールは本文生成に専念）

## コード内で利用しているクラス・関数のファイルパス一覧

- `OpenAISettings`: `src/slack_agent/config.py`
- `semche_search`: `src/slack_agent/tools/semche.py`
- `ChatOpenAI`: `langchain_openai`
- `create_agent` / `Tool`: `langchain.agents`
- `AIMessage`: `langchain_core.messages`
