#!/usr/bin/env python3
"""Summarize news / paper items using the Claude API.

ANTHROPIC_API_KEY が設定されていれば Claude API を呼び出し日本語要約を生成する。
未設定時はタイトル + 原文スニペットをそのまま返すフォールバック動作。
"""
from __future__ import annotations

import os
import sys
from typing import Iterable


PROMPT_NEWS = """あなたはディープテック専門のテクニカルアナリストです。
以下の英語ニュース本文を読んで、日本語で3-5文に要約してください。

要約には必ず含めること:
1. 何が発表/報告されたか
2. なぜ重要か (技術的進歩性 / 市場インパクト)
3. 競合や関連技術との違い

本文:
---
{title}

{body}
---
"""

PROMPT_PAPER = """あなたはAI研究者です。以下の arXiv 論文のアブストラクトを読んで、
日本語で3-5文に要約し、さらに「進歩性のポイント」を1-2行で明示してください。

出力フォーマット:
要約: ...
進歩性: ...

論文:
---
タイトル: {title}
著者: {authors}
Abstract: {body}
---
"""


def _client():
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def summarize_news(title: str, body: str, model: str = "claude-sonnet-4-6") -> str:
    client = _client()
    if client is None:
        return (body or title)[:400]
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": PROMPT_NEWS.format(title=title, body=body or "")}],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[summarize] news fallback: {e}\n")
        return (body or title)[:400]


def summarize_paper(title: str, authors: Iterable[str], body: str, model: str = "claude-sonnet-4-6") -> str:
    client = _client()
    if client is None:
        return f"要約: {(body or title)[:300]}\n進歩性: (Claude API 未設定のためフォールバック)"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_PAPER.format(
                        title=title,
                        authors=", ".join(list(authors)[:5]),
                        body=body or "",
                    ),
                }
            ],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[summarize] paper fallback: {e}\n")
        return f"要約: {(body or title)[:300]}\n進歩性: (要約失敗)"
