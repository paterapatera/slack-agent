from __future__ import annotations

import types
from typing import Any

import pytest

import slack_agent.handlers.message as message_handler

try:
    from slack_sdk.errors import SlackApiError
except ImportError:
    # テスト環境でもフォールバック定義を利用
    class SlackApiError(Exception):  # type: ignore[no-redef]
        def __init__(self, message: str = "", response: dict[str, Any] | None = None):
            super().__init__(message)
            self.response = response or {}


class _DummyApp:
    def __init__(self) -> None:
        self.client = types.SimpleNamespace()
        self.add_calls: list[dict[str, Any]] = []

        def reactions_add(**kwargs: Any) -> None:  # noqa: D401
            self.add_calls.append(kwargs)

        self.client.reactions_add = reactions_add  # type: ignore[attr-defined]

    # slack_bolt.App 互換で event デコレータを模倣（ハンドラーを保存）
    def event(self, _name: str):  # type: ignore[override]
        def decorator(func):
            self._handler = func  # type: ignore[attr-defined]
            return func
        return decorator


def test_reaction_added_before_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    # arrange
    dummy_app = _DummyApp()

    # invoke_agent をモックして即値返却（async 関数として）
    async def _fake_invoke(_q: str) -> str:
        return "ok"

    monkeypatch.setattr("slack_agent.handlers.message.invoke_agent", _fake_invoke)

    # register を呼び出してハンドラー登録
    message_handler.register(dummy_app)  # type: ignore[arg-type]

    # act: ハンドラー実行
    event = {"text": "<@U123> hello", "channel": "C1", "ts": "111.222"}

    # say ダミー
    say_messages: list[str] = []

    def say(msg: str, thread_ts: str | None = None) -> None:  # noqa: D401
        say_messages.append(msg + (f"|thread:{thread_ts}" if thread_ts else ""))

    dummy_app._handler(event=event, say=say)  # type: ignore[attr-defined]

    # assert: reactions_add が先に1回呼ばれている
    assert len(dummy_app.add_calls) == 1
    assert dummy_app.add_calls[0]["name"] == "eyes"
    assert say_messages[0].startswith("ok")


def test_reaction_error_already_reacted_continues_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """already_reacted エラーでも処理継続することを検証。"""
    # arrange
    dummy_app = _DummyApp()

    # reactions_add で already_reacted エラーを発生させる
    def reactions_add_error(**kwargs: Any) -> None:  # noqa: D401
        dummy_app.add_calls.append(kwargs)
        raise SlackApiError("already_reacted", response={"error": "already_reacted"})

    dummy_app.client.reactions_add = reactions_add_error  # type: ignore[attr-defined]

    async def _fake_invoke(_q: str) -> str:
        return "response"

    monkeypatch.setattr("slack_agent.handlers.message.invoke_agent", _fake_invoke)
    message_handler.register(dummy_app)  # type: ignore[arg-type]

    # act
    event = {"text": "<@U123> test", "channel": "C1", "ts": "222.333"}
    say_messages: list[str] = []

    def say(msg: str, thread_ts: str | None = None) -> None:  # noqa: D401
        say_messages.append(msg)

    dummy_app._handler(event=event, say=say)  # type: ignore[attr-defined]

    # assert: エラーでも応答が返される
    assert len(say_messages) == 1
    assert say_messages[0] == "response"


def test_reaction_error_missing_scope_continues_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """missing_scope エラーでも処理継続することを検証。"""
    # arrange
    dummy_app = _DummyApp()

    def reactions_add_error(**kwargs: Any) -> None:  # noqa: D401
        dummy_app.add_calls.append(kwargs)
        raise SlackApiError("missing_scope", response={"error": "missing_scope"})

    dummy_app.client.reactions_add = reactions_add_error  # type: ignore[attr-defined]

    async def _fake_invoke(_q: str) -> str:
        return "response2"

    monkeypatch.setattr("slack_agent.handlers.message.invoke_agent", _fake_invoke)
    message_handler.register(dummy_app)  # type: ignore[arg-type]

    # act
    event = {"text": "<@U123> test", "channel": "C1", "ts": "333.444"}
    say_messages: list[str] = []

    def say(msg: str, thread_ts: str | None = None) -> None:  # noqa: D401
        say_messages.append(msg)

    dummy_app._handler(event=event, say=say)  # type: ignore[attr-defined]

    # assert
    assert len(say_messages) == 1
    assert say_messages[0] == "response2"


def test_reaction_error_ratelimited_continues_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ratelimited エラーでも処理継続することを検証。"""
    # arrange
    dummy_app = _DummyApp()

    def reactions_add_error(**kwargs: Any) -> None:  # noqa: D401
        dummy_app.add_calls.append(kwargs)
        raise SlackApiError("ratelimited", response={"error": "ratelimited"})

    dummy_app.client.reactions_add = reactions_add_error  # type: ignore[attr-defined]

    async def _fake_invoke(_q: str) -> str:
        return "response3"

    monkeypatch.setattr("slack_agent.handlers.message.invoke_agent", _fake_invoke)
    message_handler.register(dummy_app)  # type: ignore[arg-type]

    # act
    event = {"text": "<@U123> test", "channel": "C1", "ts": "444.555"}
    say_messages: list[str] = []

    def say(msg: str, thread_ts: str | None = None) -> None:  # noqa: D401
        say_messages.append(msg)

    dummy_app._handler(event=event, say=say)  # type: ignore[attr-defined]

    # assert
    assert len(say_messages) == 1
    assert say_messages[0] == "response3"


def test_reaction_unexpected_error_continues_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """予期しないエラーでも処理継続することを検証。"""
    # arrange
    dummy_app = _DummyApp()

    def reactions_add_error(**kwargs: Any) -> None:  # noqa: D401
        dummy_app.add_calls.append(kwargs)
        raise RuntimeError("unexpected error")

    dummy_app.client.reactions_add = reactions_add_error  # type: ignore[attr-defined]

    async def _fake_invoke(_q: str) -> str:
        return "response4"

    monkeypatch.setattr("slack_agent.handlers.message.invoke_agent", _fake_invoke)
    message_handler.register(dummy_app)  # type: ignore[arg-type]

    # act
    event = {"text": "<@U123> test", "channel": "C1", "ts": "555.666"}
    say_messages: list[str] = []

    def say(msg: str, thread_ts: str | None = None) -> None:  # noqa: D401
        say_messages.append(msg)

    dummy_app._handler(event=event, say=say)  # type: ignore[attr-defined]

    # assert
    assert len(say_messages) == 1
    assert say_messages[0] == "response4"

