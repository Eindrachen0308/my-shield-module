#!/usr/bin/env python3
"""Fetch recent papers from arXiv and (optionally) OpenReview.

主要国際学会 (ICLR / CVPR / NeurIPS / ICML / ICRA / CoRL) に紐づく arXiv
クエリを sources.yaml から読み込み、直近 N 日に公開された論文を収集する。
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
    import arxiv  # type: ignore
    import yaml  # type: ignore
except ImportError as e:
    sys.stderr.write(
        f"[fetch_papers] Missing dependency ({e}). Run: pip install -r requirements.txt\n"
    )
    raise


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = REPO_ROOT / "sources.yaml"


@dataclass
class PaperItem:
    conference: str
    title: str
    url: str
    authors: list[str]
    published: str
    summary: str
    categories: list[str]


def load_sources() -> dict:
    with SOURCES_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def search_arxiv(query: str, max_results: int) -> list[arxiv.Result]:
    client = arxiv.Client(page_size=max_results, delay_seconds=3.0, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    return list(client.results(search))


def collect(days: int, per_conf: int) -> list[PaperItem]:
    sources = load_sources()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    items: list[PaperItem] = []

    for conf in sources.get("conferences", []):
        name = conf["name"]
        for kw in conf.get("arxiv_keywords", []):
            try:
                results = search_arxiv(kw, per_conf)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"[fetch_papers] WARN {name} {kw!r}: {e}\n")
                continue
            for r in results:
                if r.published and r.published < since:
                    continue
                items.append(
                    PaperItem(
                        conference=name,
                        title=r.title.strip(),
                        url=r.entry_id,
                        authors=[a.name for a in r.authors],
                        published=r.published.isoformat() if r.published else "",
                        summary=(r.summary or "").strip(),
                        categories=[c for c in r.categories],
                    )
                )

    # arXiv カテゴリ横断（ロボティクス / CV / LG など）の最新を追加収集
    for cat in sources.get("arxiv_categories", []):
        try:
            results = search_arxiv(f"cat:{cat}", per_conf)
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"[fetch_papers] WARN cat:{cat}: {e}\n")
            continue
        for r in results:
            if r.published and r.published < since:
                continue
            items.append(
                PaperItem(
                    conference=f"arXiv:{cat}",
                    title=r.title.strip(),
                    url=r.entry_id,
                    authors=[a.name for a in r.authors],
                    published=r.published.isoformat() if r.published else "",
                    summary=(r.summary or "").strip(),
                    categories=[c for c in r.categories],
                )
            )

    items.sort(key=lambda x: x.published, reverse=True)
    return items


def dump_json(items: Iterable[PaperItem], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch arXiv papers for major AI/ML venues")
    p.add_argument("--days", type=int, default=7, help="how many days back to look")
    p.add_argument("--per-conf", type=int, default=20, help="max results per query")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "papers.json")
    args = p.parse_args()

    items = collect(args.days, args.per_conf)
    dump_json(items, args.out)
    print(f"[fetch_papers] collected {len(items)} papers -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
