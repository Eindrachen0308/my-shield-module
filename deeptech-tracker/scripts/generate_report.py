#!/usr/bin/env python3
"""Generate daily deep-tech news report and weekly conference paper report.

Usage:
    python scripts/generate_report.py --mode daily
    python scripts/generate_report.py --mode conference
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build"
DAILY_DIR = REPO_ROOT / "reports" / "daily"
CONF_DIR = REPO_ROOT / "reports" / "conferences"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from summarize import summarize_news, summarize_paper  # noqa: E402


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dedupe(items: list[dict], key: str = "title") -> list[dict]:
    seen = set()
    out = []
    for i in items:
        k = (i.get(key) or "").strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(i)
    return out


def generate_daily(target_date: dt.date, top_n: int = 5) -> Path:
    news_path = BUILD_DIR / "news.json"
    if not news_path.exists():
        run([sys.executable, str(REPO_ROOT / "scripts" / "fetch_news.py"), "--days", "2"])
    items = dedupe(load_json(news_path))

    # Physical AI 関連を優先しつつ、カテゴリ分散を確保する
    selected: list[dict] = []
    used_categories: set[str] = set()
    for item in items:
        cat = item.get("category", "")
        if cat in used_categories:
            continue
        selected.append(item)
        used_categories.add(cat)
        if len(selected) >= top_n:
            break
    # top_n に満たない場合は priority 順に追加
    for item in items:
        if len(selected) >= top_n:
            break
        if item in selected:
            continue
        selected.append(item)

    out = DAILY_DIR / f"{target_date.isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# DeepTech Daily — {target_date.isoformat()}")
    lines.append("")
    lines.append("本日のディープテック注目ニュース TOP 5 を自動収集しました。")
    lines.append("Physical AI（ヒューマノイド / 自動運転 / VLA）を優先し、量子・フュージョン・バイオなどの分野もカバーしています。")
    lines.append("")
    for idx, item in enumerate(selected[:top_n], 1):
        title = item.get("title", "(no title)")
        url = item.get("url", "")
        label = item.get("category_label", item.get("category", ""))
        published = item.get("published", "")[:10]
        summary_ja = summarize_news(title, item.get("summary", ""))
        lines.append(f"## {idx}. {title}")
        lines.append("")
        lines.append(f"- カテゴリ: **{label}**")
        lines.append(f"- 公開日: {published}")
        lines.append(f"- URL: {url}")
        lines.append("")
        lines.append(summary_ja)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_本レポートは GitHub Actions (`deeptech-daily.yml`) で自動生成されました。_")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[generate_report] wrote {out}")
    return out


def generate_conference(target_date: dt.date, top_n: int = 10) -> Path:
    papers_path = BUILD_DIR / "papers.json"
    if not papers_path.exists():
        run([sys.executable, str(REPO_ROOT / "scripts" / "fetch_papers.py"), "--days", "7"])
    items = dedupe(load_json(papers_path))

    # 学会タグを持つものを優先
    conf_items = [i for i in items if not i.get("conference", "").startswith("arXiv:")]
    arxiv_items = [i for i in items if i.get("conference", "").startswith("arXiv:")]
    selected = (conf_items + arxiv_items)[:top_n]

    out = CONF_DIR / f"{target_date.isoformat()}_weekly.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# DeepTech Conference Papers — week of {target_date.isoformat()}")
    lines.append("")
    lines.append("ICLR / CVPR / NeurIPS / ICML / ICRA / CoRL および arXiv カテゴリ (cs.RO / cs.CV / cs.LG / cs.AI) から")
    lines.append("直近 1 週間に更新された論文を収集し、要約と進歩性のポイントをまとめました。")
    lines.append("")
    for idx, item in enumerate(selected, 1):
        title = item.get("title", "(no title)")
        url = item.get("url", "")
        conf = item.get("conference", "")
        published = item.get("published", "")[:10]
        authors = item.get("authors", [])
        summary_ja = summarize_paper(title, authors, item.get("summary", ""))
        lines.append(f"## {idx}. {title}")
        lines.append("")
        lines.append(f"- 学会 / カテゴリ: **{conf}**")
        lines.append(f"- 公開日: {published}")
        lines.append(f"- 著者: {', '.join(authors[:5])}{'...' if len(authors) > 5 else ''}")
        lines.append(f"- URL: {url}")
        lines.append("")
        lines.append(summary_ja)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_本レポートは GitHub Actions (`deeptech-papers-weekly.yml`) で自動生成されました。_")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[generate_report] wrote {out}")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["daily", "conference"], required=True)
    p.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (default: today)")
    p.add_argument("--top", type=int, default=None)
    args = p.parse_args()

    target = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    if args.mode == "daily":
        generate_daily(target, top_n=args.top or 5)
    else:
        generate_conference(target, top_n=args.top or 10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
