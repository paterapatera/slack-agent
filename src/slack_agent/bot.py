from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import SlackSettings
from .handlers import message


def build_app() -> App:
    """Slack Bolt アプリケーションを構築して返します。"""
    settings = SlackSettings.from_env()
    app = App(token=settings.bot_token)
    # ハンドラーを登録
    message.register(app)
    return app


def main() -> None:
    """Socket Mode でアプリを起動します。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger = logging.getLogger("slack_agent")
    app = build_app()
    settings = SlackSettings.from_env()
    handler = SocketModeHandler(app, settings.app_token)
    # start() はブロッキング呼び出し（外部ライブラリ）なので型未解析として扱う
    logger.info("Starting Socket Mode handler...")
    handler.start()  # type: ignore[no-untyped-call]


if __name__ == "__main__":  # pragma: no cover
    main()
