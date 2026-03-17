#!/usr/bin/env python3
"""X Talent Sourcing Agent - Main entry point.

X (Twitter) のツイートやプロフィール情報を検索し、
指定のペルソナに合致する人材をA/B/Cランクでソーシングするエージェント。
"""

import os
import sys
import csv
import json
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from persona import PersonaCriteria, collect_persona_interactive
from x_client import XClient
from scorer import rank_candidates, Rank, ScoredCandidate

console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════╗
║         X 人材ソーシング エージェント v1.0              ║
║                                                          ║
║   Xのツイート・プロフィールから人材を発見し、            ║
║   A/B/Cランクで評価・レコメンドします                    ║
╚══════════════════════════════════════════════════════════╝
"""


def display_results(candidates: list[ScoredCandidate], persona: PersonaCriteria):
    """Display sourcing results in a formatted table."""
    rank_groups = {Rank.A: [], Rank.B: [], Rank.C: []}
    for c in candidates:
        rank_groups[c.rank].append(c)

    # Summary
    console.print(
        Panel(
            f"[bold]検索結果サマリー[/bold]\n\n"
            f"  合計候補者数: {len(candidates)}名\n"
            f"  Aランク（高合致）: {len(rank_groups[Rank.A])}名\n"
            f"  Bランク（中合致）: {len(rank_groups[Rank.B])}名\n"
            f"  Cランク（可能性あり）: {len(rank_groups[Rank.C])}名",
            title="結果サマリー",
            border_style="green",
        )
    )

    # Rank A
    if rank_groups[Rank.A]:
        console.print("\n[bold red]━━━ Aランク：ペルソナ合致度が高い ━━━[/bold red]\n")
        _display_rank_table(rank_groups[Rank.A], "red")

    # Rank B
    if rank_groups[Rank.B]:
        console.print(
            "\n[bold yellow]━━━ Bランク：ある程度合致 ━━━[/bold yellow]\n"
        )
        _display_rank_table(rank_groups[Rank.B], "yellow")

    # Rank C
    if rank_groups[Rank.C]:
        console.print(
            "\n[bold blue]━━━ Cランク：合致度は緩いが可能性あり ━━━[/bold blue]\n"
        )
        _display_rank_table(rank_groups[Rank.C], "blue")


def _display_rank_table(candidates: list[ScoredCandidate], color: str):
    """Display a table for a specific rank group."""
    table = Table(show_header=True, header_style=f"bold {color}")
    table.add_column("スコア", width=8, justify="center")
    table.add_column("ユーザー", width=20)
    table.add_column("プロフィール", width=35)
    table.add_column("マッチ理由", width=35)
    table.add_column("URL", width=25)

    for c in candidates:
        reasons = "\n".join(c.match_reasons[:3])
        bio = c.profile.bio[:80] + ("..." if len(c.profile.bio) > 80 else "")
        table.add_row(
            f"{c.score}/100",
            f"@{c.profile.username}\n({c.profile.name})\nフォロワー: {c.profile.followers_count:,}",
            bio,
            reasons,
            c.profile.profile_url,
        )

    console.print(table)


def _display_candidate_detail(candidate: ScoredCandidate):
    """Display detailed info for a single candidate."""
    p = candidate.profile
    console.print(
        Panel(
            f"[bold]@{p.username}[/bold] ({p.name})\n\n"
            f"ランク: {candidate.rank.value} | スコア: {candidate.score}/100\n\n"
            f"プロフィール:\n{p.bio}\n\n"
            f"場所: {p.location or '未設定'}\n"
            f"フォロワー: {p.followers_count:,} | "
            f"フォロー: {p.following_count:,} | "
            f"ツイート数: {p.tweet_count:,}\n\n"
            f"マッチキーワード: {', '.join(candidate.matched_keywords)}\n\n"
            f"マッチ理由:\n"
            + "\n".join(f"  - {r}" for r in candidate.match_reasons)
            + f"\n\nポテンシャル:\n  {candidate.potential_notes}\n\n"
            f"最近のツイート:\n"
            + "\n".join(f"  > {t[:100]}" for t in p.recent_tweets[:5])
            + f"\n\nURL: {p.profile_url}",
            title=f"候補者詳細 - @{p.username}",
            border_style="cyan",
        )
    )


def export_to_csv(candidates: list[ScoredCandidate], filename: str):
    """Export results to CSV."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "ランク",
                "スコア",
                "ユーザー名",
                "名前",
                "プロフィール",
                "フォロワー数",
                "場所",
                "マッチキーワード",
                "マッチ理由",
                "ポテンシャル",
                "URL",
            ]
        )
        for c in candidates:
            writer.writerow(
                [
                    c.rank.value,
                    c.score,
                    c.profile.username,
                    c.profile.name,
                    c.profile.bio,
                    c.profile.followers_count,
                    c.profile.location,
                    ", ".join(c.matched_keywords),
                    " / ".join(c.match_reasons),
                    c.potential_notes,
                    c.profile.profile_url,
                ]
            )
    console.print(f"\n[green]CSVファイルに出力しました: {filename}[/green]")


def export_to_json(candidates: list[ScoredCandidate], filename: str):
    """Export results to JSON."""
    data = []
    for c in candidates:
        data.append(
            {
                "rank": c.rank.value,
                "score": c.score,
                "profile": c.profile.to_dict(),
                "match_reasons": c.match_reasons,
                "matched_keywords": c.matched_keywords,
                "potential_notes": c.potential_notes,
            }
        )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"\n[green]JSONファイルに出力しました: {filename}[/green]")


def post_search_menu(candidates: list[ScoredCandidate], persona: PersonaCriteria):
    """Interactive menu after search results are displayed."""
    while True:
        console.print("\n[bold]次のアクションを選択してください:[/bold]")
        console.print("  1. 候補者の詳細を表示")
        console.print("  2. CSVにエクスポート")
        console.print("  3. JSONにエクスポート")
        console.print("  4. 検索条件を変えて再検索")
        console.print("  5. 終了")

        choice = input("\n選択 (1-5): ").strip()

        if choice == "1":
            username = input("ユーザー名を入力 (@なし): ").strip()
            found = [c for c in candidates if c.profile.username == username]
            if found:
                _display_candidate_detail(found[0])
            else:
                console.print("[red]該当する候補者が見つかりません[/red]")

        elif choice == "2":
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sourcing_results_{ts}.csv"
            export_to_csv(candidates, filename)

        elif choice == "3":
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sourcing_results_{ts}.json"
            export_to_json(candidates, filename)

        elif choice == "4":
            return True  # Signal to restart

        elif choice == "5":
            console.print("\n[bold green]お疲れ様でした！[/bold green]\n")
            return False

        else:
            console.print("[red]1-5の数字を入力してください[/red]")


def run_sourcing(persona: PersonaCriteria, x_client: XClient, anthropic_key: str | None):
    """Execute the sourcing pipeline."""
    console.print("\n[bold cyan]検索を開始します...[/bold cyan]\n")

    queries = persona.get_search_queries()
    console.print(f"生成された検索クエリ数: {len(queries)}")
    for i, q in enumerate(queries[:10], 1):
        console.print(f"  {i}. {q}")
    if len(queries) > 10:
        console.print(f"  ... 他 {len(queries) - 10} クエリ")

    # Search
    console.print("\n[yellow]Xからユーザーを検索中...[/yellow]")
    profiles = x_client.search_users_by_keywords(
        keywords=queries[:15],  # Limit to avoid rate limits
        max_results_per_keyword=20,
    )
    console.print(f"[green]ユニークユーザー {len(profiles)}名 を発見[/green]")

    if not profiles:
        console.print("[red]候補者が見つかりませんでした。キーワードを変更してみてください。[/red]")
        return None

    # Score and rank
    console.print("\n[yellow]候補者を評価・ランク付け中...[/yellow]")
    candidates = rank_candidates(profiles, persona, anthropic_key)

    if not candidates:
        console.print("[red]スコアリング後に候補者が残りませんでした。[/red]")
        return None

    console.print(f"[green]評価完了！ {len(candidates)}名の候補者をランク付けしました[/green]\n")

    # Display
    display_results(candidates, persona)
    return candidates


def main():
    load_dotenv()

    console.print(BANNER)

    # Check API keys
    bearer_token = os.getenv("X_BEARER_TOKEN")
    if not bearer_token:
        console.print(
            "[red][Error] X_BEARER_TOKEN が設定されていません。[/red]\n"
            ".env ファイルに X_BEARER_TOKEN を設定してください。\n"
            "取得先: https://developer.x.com/en/portal/dashboard"
        )
        sys.exit(1)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        console.print(
            "[yellow][Warning] ANTHROPIC_API_KEY が未設定です。"
            "キーワードベースの簡易評価のみ使用します。[/yellow]\n"
            "より精度の高い評価にはAnthropic APIキーを設定してください。"
        )

    x_client = XClient(bearer_token)

    while True:
        # Collect persona
        persona = collect_persona_interactive()

        # Confirm before search
        console.print("\n[bold]この設定で検索を開始しますか？[/bold]")
        confirm = input("開始する場合は Enter、修正する場合は 'n': ").strip()
        if confirm.lower() == "n":
            continue

        # Run sourcing
        candidates = run_sourcing(persona, x_client, anthropic_key)

        if candidates:
            should_restart = post_search_menu(candidates, persona)
            if not should_restart:
                break
        else:
            retry = input("\n条件を変えて再検索しますか？ (y/n): ").strip()
            if retry.lower() != "y":
                break


if __name__ == "__main__":
    main()
