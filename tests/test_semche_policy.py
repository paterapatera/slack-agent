from __future__ import annotations

import re
from pathlib import Path

import slack_agent.agent as agent_mod


def test_system_prompt_contains_policy(tmp_path: Path) -> None:
    """system_prompt にポリシー文言が含まれることを検証。"""
    # 直接 private 変数へのアクセスは避け、agentモジュールのソースを読み込む簡易検証
    source = Path(agent_mod.__file__).read_text(encoding="utf-8")
    # system_prompt が結合されている部分にキーワードが入っているか
    assert "Semche の検索" in source  # 具体関数名ではなく一般的な表現
    assert "include_documents=True" in source
    assert "max_content_length=None" in source
    # 社内業務情報の記述キーワード（社内仕様）
    assert re.search("社内業務情報", source)
