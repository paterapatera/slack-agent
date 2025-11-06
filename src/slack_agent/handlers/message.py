from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from slack_bolt import App
from slack_bolt.context.say.say import Say

from ..agent import invoke_agent
from ..text import clean_mention_text


def register(app: App) -> None:
    """`app_mention` イベントのハンドラーを登録します。"""
    logger = logging.getLogger("slack_agent.handlers.message")

    @app.event("app_mention")
    def handle_app_mention(event: Mapping[str, Any], say: Say) -> None:
        # event は Slack から送られてくる生のイベントペイロード
        text: str = event.get("text", "")
        cleaned = clean_mention_text(text)
        # スレッド返信にする: 返信先の thread_ts は既存の thread_ts または元メッセージの ts
        thread_ts = event.get("thread_ts") or event.get("ts")
        logger.info(
            "app_mention received: text=%r cleaned=%r thread_ts=%r",
            text,
            cleaned,
            thread_ts,
        )

        try:
            # エージェントに質問を投げて応答を取得
            # asyncio.run() で非同期関数を同期的に実行
            answer = asyncio.run(invoke_agent(cleaned))
            logger.info("Agent answer: %r", answer)

            # 応答をスレッドに返信
            say(answer, thread_ts=thread_ts)

        except Exception as e:
            # エラーハンドリング: ユーザーフレンドリーなメッセージを返信
            error_message = f"申し訳ありません。エラーが発生しました: {e}"
            logger.error("Error invoking agent: %s", e, exc_info=True)
            say(error_message, thread_ts=thread_ts)
