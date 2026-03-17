"""Persona definition and interactive questionnaire for talent sourcing."""

from dataclasses import dataclass, field


@dataclass
class PersonaCriteria:
    """Defines the target persona for sourcing."""

    purpose: str  # 採用目的（例: エンジニア採用、業務委託、共同研究）
    role_description: str  # 求める人物像の説明
    must_keywords: list[str] = field(default_factory=list)  # 必須キーワード
    want_keywords: list[str] = field(default_factory=list)  # あると望ましいキーワード
    nice_keywords: list[str] = field(default_factory=list)  # あれば加点のキーワード
    location: str = ""  # 希望勤務地
    min_followers: int = 0  # 最小フォロワー数
    language: str = "ja"  # 対象言語

    def get_search_queries(self) -> list[str]:
        """Generate search queries from keywords."""
        queries = []
        # must_keywords から主要なクエリを生成
        for kw in self.must_keywords:
            queries.append(kw)
        # want_keywords の組み合わせ
        for kw in self.want_keywords:
            queries.append(kw)
        # must + want の組み合わせ
        for m in self.must_keywords[:3]:
            for w in self.want_keywords[:3]:
                queries.append(f"{m} {w}")
        return queries

    def to_prompt_context(self) -> str:
        """Convert to a text description for LLM scoring."""
        lines = [
            f"## ターゲットペルソナ",
            f"**目的**: {self.purpose}",
            f"**求める人物像**: {self.role_description}",
            f"**必須キーワード**: {', '.join(self.must_keywords)}",
            f"**推奨キーワード**: {', '.join(self.want_keywords)}",
            f"**加点キーワード**: {', '.join(self.nice_keywords)}",
        ]
        if self.location:
            lines.append(f"**希望エリア**: {self.location}")
        if self.min_followers > 0:
            lines.append(f"**最小フォロワー数**: {self.min_followers}")
        return "\n".join(lines)


def collect_persona_interactive() -> PersonaCriteria:
    """Interactive questionnaire to define the target persona."""
    print("\n" + "=" * 60)
    print("  X人材ソーシング エージェント - ペルソナ設定")
    print("=" * 60)

    print("\n📋 まず、ソーシングの目的と対象について教えてください。\n")

    # 1. 目的
    print("【Q1】どんな目的で人材を探していますか？")
    print("  1. 正社員採用")
    print("  2. 業務委託・フリーランス")
    print("  3. 副業人材")
    print("  4. 共同研究・アカデミア連携")
    print("  5. コミュニティ / イベント登壇者")
    print("  6. その他")
    purpose_choice = input("\n選択肢の番号を入力 (1-6): ").strip()
    purpose_map = {
        "1": "正社員採用",
        "2": "業務委託・フリーランス",
        "3": "副業人材",
        "4": "共同研究・アカデミア連携",
        "5": "コミュニティ / イベント登壇者",
        "6": "その他",
    }
    purpose = purpose_map.get(purpose_choice, "その他")
    if purpose == "その他":
        purpose = input("具体的な目的を入力してください: ").strip()
    print(f"  → 目的: {purpose}\n")

    # 2. 人物像
    print("【Q2】どんな人を探していますか？")
    print("  （例: Pythonが得意なバックエンドエンジニア、")
    print("   機械学習の研究経験があるデータサイエンティスト、など）")
    role_description = input("\n人物像を自由に記述: ").strip()
    print(f"  → 人物像: {role_description}\n")

    # 3. 必須キーワード
    print("【Q3】必須の検索キーワードを入力してください。")
    print("  （カンマ区切りで複数入力可。例: Python,機械学習,データ分析）")
    must_input = input("\n必須キーワード: ").strip()
    must_keywords = [k.strip() for k in must_input.split(",") if k.strip()]
    print(f"  → 必須: {must_keywords}\n")

    # 4. 推奨キーワード
    print("【Q4】あると望ましいキーワードを入力してください。")
    print("  （カンマ区切り。例: AWS,Docker,Kubernetes）")
    want_input = input("\n推奨キーワード: ").strip()
    want_keywords = [k.strip() for k in want_input.split(",") if k.strip()]
    print(f"  → 推奨: {want_keywords}\n")

    # 5. 加点キーワード
    print("【Q5】あれば加点となるキーワードを入力してください。")
    print("  （カンマ区切り。例: OSS貢献,登壇経験,技術ブログ）")
    nice_input = input("\n加点キーワード: ").strip()
    nice_keywords = [k.strip() for k in nice_input.split(",") if k.strip()]
    print(f"  → 加点: {nice_keywords}\n")

    # 6. エリア
    print("【Q6】希望勤務地・エリアはありますか？（任意、空欄でスキップ）")
    location = input("\nエリア: ").strip()

    # 7. 最小フォロワー数
    print("\n【Q7】最小フォロワー数の目安はありますか？（任意、空欄で0）")
    print("  （影響力のある人を探す場合に設定。例: 500）")
    followers_input = input("\n最小フォロワー数: ").strip()
    min_followers = int(followers_input) if followers_input.isdigit() else 0

    persona = PersonaCriteria(
        purpose=purpose,
        role_description=role_description,
        must_keywords=must_keywords,
        want_keywords=want_keywords,
        nice_keywords=nice_keywords,
        location=location,
        min_followers=min_followers,
    )

    print("\n" + "-" * 60)
    print("  ペルソナ設定が完了しました！")
    print("-" * 60)
    print(persona.to_prompt_context())
    print("-" * 60 + "\n")

    return persona
