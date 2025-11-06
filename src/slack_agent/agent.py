from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain import agents as lc_agents
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .config import OpenAISettings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_agent_graph() -> Any:
    """LangChain Agents API で compiled agent graph を生成（キャッシュ）。

    - create_agent（新API）を使用
    - 現時点ではツールは未登録（純粋な対話）
    """
    settings = OpenAISettings.from_env()
    llm = ChatOpenAI(model=settings.model, api_key=SecretStr(settings.api_key), temperature=0.7)

    # System プロンプト（Slack向けに簡潔に）
    system_prompt = "You are a helpful assistant. Answer concisely for Slack replies."

    # tools は未使用
    tools = None

    graph: Any = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
    logger.info("Agent graph created with model=%s", settings.model)
    return graph


async def invoke_agent(question: str) -> str:
    """Agents API 経由で質問を投げ、最終出力文字列を返します。"""
    graph = get_agent_graph()
    try:
        # Agents API は messages ベースのステートを返す
        state = await graph.ainvoke({
            "messages": [{"role": "user", "content": question}],
        })
        messages = state.get("messages", [])
        # 最後の AI 出力を抽出
        answer_text = None
        if messages:
            last = messages[-1]
            if isinstance(last, AIMessage):
                answer_text = last.content
            else:
                # dict 形式などの場合へのフォールバック
                answer_text = getattr(last, "content", None) or getattr(last, "text", None)
        return str(answer_text) if answer_text is not None else ""
    except Exception as e:
        logger.error("Agent invocation failed: %s", e, exc_info=True)
        raise
