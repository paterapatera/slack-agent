from __future__ import annotations

import asyncio
import os
import atexit
import contextlib
import logging
import threading
from collections.abc import Coroutine, Mapping
from concurrent.futures import Future
from typing import Any, TypeVar

from slack_bolt import App
from slack_bolt.context.say.say import Say

try:  # slack_sdk は slack-bolt 依存に含まれる想定。万一未導入でも処理継続できるようフォールバック。
    from slack_sdk.errors import SlackApiError
except Exception:  # pragma: no cover - インポート失敗はまれ
    class SlackApiError(Exception):  # type: ignore
        """フォールバック: SlackApiError が未インポート時の簡易例外クラス"""

        def __init__(
            self,
            message: str = "SlackApiError fallback",
            response: dict[str, Any] | None = None,
        ):
            super().__init__(message)
            self.response = response or {}

from ..agent import invoke_agent
from ..text import clean_mention_text

# --- 背景イベントループ（永続）で非同期関数を実行する仕組み ------------------------
# Slack Bolt の同期ハンドラー内で asyncio.run() を使うと、処理後にイベントループが
# クローズされ、そこで生成された MCP セッションの下層ストリームも閉じられてしまう。
# これを避けるため、プロセス中に存続する専用のイベントループを別スレッドで動かし、
# そのループ上でエージェント実行を行う。

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_ready = threading.Event()


def _start_background_loop() -> None:
    global _bg_loop, _bg_thread
    if _bg_loop is not None:
        return

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            # 共有参照をセットしてから run_forever
            global _bg_loop
            _bg_loop = loop
            _bg_ready.set()
            loop.run_forever()
        finally:
            # ループ停止時のクローズ
            with contextlib.suppress(Exception):
                loop.close()

    t = threading.Thread(target=_runner, name="slack-agent-bg-loop", daemon=True)
    _bg_thread = t
    t.start()
    _bg_ready.wait(timeout=5)


def _stop_background_loop() -> None:
    global _bg_loop
    loop = _bg_loop
    if loop is None:
        return
    try:
        loop.call_soon_threadsafe(loop.stop)
    except Exception:  # noqa: BLE001
        pass
    finally:
        _bg_loop = None


atexit.register(_stop_background_loop)


T = TypeVar("T")


def _run_in_background(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047 - 単純な汎用同期ヘルパ
    """永続イベントループでコルーチンを同期的に実行して結果を返す。"""
    if _bg_loop is None:
        _start_background_loop()
    assert _bg_loop is not None  # for type checker
    fut: Future[T] = asyncio.run_coroutine_threadsafe(coro, _bg_loop)
    return fut.result()


def register(app: App) -> None:
    def fetch_thread_history(channel: str, thread_ts: str, limit: int = 10) -> list[dict[str, Any]]:
        """指定スレッドの履歴をSlack APIで取得し、直近limit件のみ返す。失敗時は空リスト。"""
        try:
            response = app.client.conversations_replies(channel=channel, ts=thread_ts, limit=limit)
            msgs: list[Any] = response.get("messages", [])  # mypy: arbitrary JSON-like
            # 型安全にキャスト（mypy用）。Slack SDKは任意型を返すため保守的にフィルタ
            messages: list[dict[str, Any]] = [m for m in msgs if isinstance(m, dict)]
            # スレッドの時系列順で直近limit件のみ返す
            return messages[-limit:] if len(messages) > limit else messages
        except Exception as e:
            logger.warning(f"Failed to fetch thread history: {e}")
            return []
    """`app_mention` イベントのハンドラーを登録します。"""
    logger = logging.getLogger("slack_agent.handlers.message")

    def _try_add_eyes_reaction(app: App, event: Mapping[str, Any]) -> None:
        """対象メッセージに :eyes: リアクションを付与（失敗しても処理は継続）。"""
        channel = event.get("channel")
        ts = event.get("ts")
        if not channel or not ts:
            logger.debug("Skip adding reaction: missing channel/ts in event")
            return
        try:
            app.client.reactions_add(channel=channel, name="eyes", timestamp=ts)
            logger.info(":eyes: reaction added channel=%s ts=%s", channel, ts)
        except SlackApiError as e:  # pragma: no cover - 詳細分岐は別テストでモック
            err = e.response.get("error") if hasattr(e, "response") else None
            if err == "already_reacted":
                logger.info("Reaction already exists for channel=%s ts=%s", channel, ts)
            elif err == "missing_scope":
                logger.warning("Cannot add reaction (missing_scope) channel=%s ts=%s", channel, ts)
            elif err == "ratelimited":
                logger.warning("Rate limited adding reaction channel=%s ts=%s", channel, ts)
            else:
                logger.warning(
                    "Failed to add :eyes: reaction err=%s channel=%s ts=%s", err, channel, ts
                )
        except Exception as e:
            logger.warning("Unexpected error adding reaction: %s", e)

    @app.event("app_mention")
    def handle_app_mention(event: Mapping[str, Any], say: Say) -> None:
        # event は Slack から送られてくる生のイベントペイロード
        text: str = event.get("text", "")
        cleaned = clean_mention_text(text)
        # スレッド返信にする: 返信先の thread_ts は既存の thread_ts または元メッセージの ts
        thread_ts = event.get("thread_ts") or event.get("ts")
        channel = event.get("channel")
        # スレッド履歴を取得
        history: list[dict[str, Any]] = []
        if channel and thread_ts:
            # 環境変数で取得件数を調整（デフォルト10）
            raw_limit = os.getenv("SLACK_HISTORY_LIMIT", "10")
            try:
                limit = max(1, min(50, int(raw_limit)))
            except Exception:
                limit = 10
            history = fetch_thread_history(channel, thread_ts, limit=limit)
            # 直近イベント（現在のメッセージ）が含まれている場合は除外して二重投入を防ぐ
            current_ts = event.get("ts")
            if current_ts:
                history = [m for m in history if m.get("ts") != current_ts]
        logger.info("Fetched thread history: %d messages", len(history))
        logger.info(
            "app_mention received: text=%r cleaned=%r thread_ts=%r",
            text,
            cleaned,
            thread_ts,
        )

        # 応答生成前に :eyes: リアクションを追加して「処理中」であることを可視化
        _try_add_eyes_reaction(app, event)

        try:
            # エージェントに質問を投げて応答を取得（永続ループ上で実行）
            # 履歴も渡す（今後の拡張で利用）。ただし古いシグネチャ互換のためフォールバックあり。
            try:
                answer = _run_in_background(invoke_agent(cleaned, history=history))
            except TypeError:
                # 旧版のinvoke_agent(question: str)のみのモック等に対応
                answer = _run_in_background(invoke_agent(cleaned))
            logger.info("Agent answer: %r", answer)

            # 応答をスレッドに返信
            say(answer, thread_ts=thread_ts)

        except Exception as e:
            # エラーハンドリング: ユーザーフレンドリーなメッセージを返信
            error_message = f"申し訳ありません。エラーが発生しました: {e}"
            logger.error("Error invoking agent: %s", e, exc_info=True)
            say(error_message, thread_ts=thread_ts)
