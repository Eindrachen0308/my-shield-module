#!/usr/bin/env python3
"""Fetch deep-tech news from RSS feeds defined in sources.yaml.

X (Twitter) 直接取得は API 制約があるため、本スクリプトでは RSS を中心に取得する。
X ポストを取り込みたい場合は `nitter` ブリッジや `twitrss.me` の RSS 出力を
sources.yaml の rss: リストに追加することで対応可能。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import feedparser  # type: ignore
    import yaml  # type: ignore
except ImportError as e:
    sys.stderr.write(
        f"[fetch_news] Missing dependency ({e}). Run: pip install -r requirements.txt\n"
    )
    raise


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = REPO_ROOT / "sources.yaml"


@dataclass
class NewsItem:
    category: str
    category_label: str
    priority: int
    title: str
    url: str
    published: str
    summary: str
    source: str


def load_sources() -> dict:
    with SOURCES_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_date(entry) -> dt.datetime:
    for key in ("published_parsed", "updated_parsed"):
        value = getattr(entry, key, None) or entry.get(key)
        if value:
            try:
                return dt.datetime(*value[:6], tzinfo=dt.timezone.utc)
            except Exception:  # noqa: BLE001
                continue
    return dt.datetime.now(dt.timezone.utc)


def fetch_feed(url: str) -> list:
    parsed = feedparser.parse(url)
    return list(parsed.entries or [])


def collect(since: dt.datetime) -> list[NewsItem]:
    sources = load_sources()
    items: list[NewsItem] = []
    for key, cfg in sources.get("categories", {}).items():
        label = cfg.get("label", key)
        priority = cfg.get("priority", 999)
        for url in cfg.get("rss", []) or []:
            try:
                entries = fetch_feed(url)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"[fetch_news] WARN {url}: {e}\n")
                continue
            for entry in entries:
                published = parse_date(entry)
                if published < since:
                    continue
                items.append(
                    NewsItem(
                        category=key,
                        category_label=label,
                        priority=priority,
                        title=(entry.get("title") or "").strip(),
                        url=entry.get("link") or "",
                        published=published.isoformat(),
                        summary=(entry.get("summary") or "").strip()[:500],
                        source=url,
                    )
                )
    items.sort(key=lambda x: (x.priority, x.published), reverse=False)
    return items


def dump_json(items: Iterable[NewsItem], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch deeptech news via RSS")
    p.add_argument("--days", type=int, default=2, help="how many days back to look")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "news.json")
    args = p.parse_args()

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    items = collect(since)
    dump_json(items, args.out)
    print(f"[fetch_news] collected {len(items)} items -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
