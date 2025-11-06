from __future__ import annotations

import pytest

from slack_agent.text import DEFAULT_EMPTY_MESSAGE, clean_mention_text


@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("<@U123> hello", "hello"),
        ("<@U123>  hello   world", "hello   world"),
        ("no mention", "no mention"),
        ("<@U123>", DEFAULT_EMPTY_MESSAGE),
        ("", DEFAULT_EMPTY_MESSAGE),
        ("   <@U123>   hey  ", "hey"),
    ],
)
def test_clean_mention_text(input_text: str, expected: str) -> None:
    assert clean_mention_text(input_text) == expected
