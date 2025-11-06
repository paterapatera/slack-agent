from __future__ import annotations

import re
from typing import Final

DEFAULT_EMPTY_MESSAGE: Final[str] = "(no message)"


_LEADING_MENTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*<@[^>]+>\s*")


def clean_mention_text(text: str) -> str:
    """メンション（先頭の <@U...>）を取り除き、前後の空白を除去した文字列を返します。

    - 入力テキストが空、またはメンション以外何も残らない場合は "(no message)" を返します。
    - 先頭にメンションがない場合はそのままトリミングのみ行います。
    """
    # 先頭のメンション（<@U...>）とその前後の空白のみを除去し、内部の空白は保持する
    cleaned = _LEADING_MENTION_RE.sub("", text, count=1).strip()
    return cleaned if cleaned else DEFAULT_EMPTY_MESSAGE
