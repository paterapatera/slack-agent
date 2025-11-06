from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class SlackSettings:
    bot_token: str
    app_token: str

    @staticmethod
    def from_env() -> SlackSettings:
        """環境変数から設定値を読み込みます。

        必須の環境変数:
        - SLACK_BOT_TOKEN: xoxb- で始まる Bot ユーザートークン
        - SLACK_APP_TOKEN: xapp- で始まる App レベルトークン（Socket Mode 用）
        """
        # .env が存在する場合は読み込む
        load_dotenv()

        bot = os.getenv("SLACK_BOT_TOKEN")
        app = os.getenv("SLACK_APP_TOKEN")

        if not bot:
            raise RuntimeError("SLACK_BOT_TOKEN が設定されていません")
        if not app:
            raise RuntimeError("SLACK_APP_TOKEN が設定されていません")

        return SlackSettings(bot_token=bot, app_token=app)
