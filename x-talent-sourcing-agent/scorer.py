"""Scoring and ranking engine for talent sourcing candidates."""

import json
from dataclasses import dataclass
from enum import Enum

import anthropic

from persona import PersonaCriteria
from x_client import XUserProfile


class Rank(str, Enum):
    A = "A"  # ペルソナ合致度が高い
    B = "B"  # ペルソナとある程度合致
    C = "C"  # 合致度は緩いが可能性あり


@dataclass
class ScoredCandidate:
    """A candidate with scoring results."""

    profile: XUserProfile
    rank: Rank
    score: int  # 0-100
    match_reasons: list[str]  # マッチした理由
    matched_keywords: list[str]  # マッチしたキーワード
    potential_notes: str  # ポテンシャルに関するメモ

    def summary(self) -> str:
        reasons = "\n    ".join(self.match_reasons)
        keywords = ", ".join(self.matched_keywords)
        return (
            f"  [{self.rank.value}ランク] @{self.profile.username} "
            f"({self.profile.name})\n"
            f"    スコア: {self.score}/100\n"
            f"    プロフィール: {self.profile.bio[:100]}...\n"
            f"    フォロワー: {self.profile.followers_count:,}\n"
            f"    マッチキーワード: {keywords}\n"
            f"    マッチ理由:\n    {reasons}\n"
            f"    ポテンシャル: {self.potential_notes}\n"
            f"    URL: {self.profile.profile_url}"
        )


def _keyword_match_score(
    text: str, must: list[str], want: list[str], nice: list[str]
) -> tuple[int, list[str]]:
    """Simple keyword matching score. Returns (score, matched_keywords)."""
    text_lower = text.lower()
    score = 0
    matched = []

    for kw in must:
        if kw.lower() in text_lower:
            score += 30
            matched.append(f"[必須] {kw}")

    for kw in want:
        if kw.lower() in text_lower:
            score += 15
            matched.append(f"[推奨] {kw}")

    for kw in nice:
        if kw.lower() in text_lower:
            score += 5
            matched.append(f"[加点] {kw}")

    return score, matched


def score_with_keywords(
    profile: XUserProfile, persona: PersonaCriteria
) -> tuple[int, list[str]]:
    """Score a candidate using keyword matching on bio + tweets."""
    combined_text = profile.bio + " " + " ".join(profile.recent_tweets)
    return _keyword_match_score(
        combined_text,
        persona.must_keywords,
        persona.want_keywords,
        persona.nice_keywords,
    )


def score_with_llm(
    profile: XUserProfile,
    persona: PersonaCriteria,
    api_key: str,
) -> dict:
    """Use Claude to evaluate a candidate against the persona.

    Returns dict with: rank, score, match_reasons, potential_notes
    """
    client = anthropic.Anthropic(api_key=api_key)

    user_info = json.dumps(profile.to_dict(), ensure_ascii=False, indent=2)

    prompt = f"""あなたは人材ソーシングの専門家です。以下のターゲットペルソナに対して、
Xユーザーの情報を分析し、マッチ度を評価してください。

{persona.to_prompt_context()}

## 候補者のX情報
{user_info}

## 評価基準
- **Aランク (スコア 70-100)**: ペルソナとの合致度が高い。必須キーワードの多くがマッチし、
  プロフィールや発信内容が求める人物像に非常に近い。
- **Bランク (スコア 40-69)**: ペルソナとある程度合致。一部のキーワードがマッチし、
  関連する経験やスキルが見られる。
- **Cランク (スコア 10-39)**: 合致度は緩いが可能性がある。直接的なマッチは少ないが、
  関連分野の経験や転用可能なスキルが見られる。

## 回答形式 (JSON)
以下のJSON形式で回答してください。JSON以外の文字は含めないでください。
{{
  "rank": "A" or "B" or "C",
  "score": 0-100の整数,
  "match_reasons": ["マッチした理由1", "マッチした理由2", ...],
  "matched_keywords": ["マッチしたキーワード1", ...],
  "potential_notes": "この候補者のポテンシャルについてのコメント"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Extract JSON from response
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)


def rank_candidates(
    profiles: dict[str, XUserProfile],
    persona: PersonaCriteria,
    anthropic_api_key: str | None = None,
) -> list[ScoredCandidate]:
    """Rank all candidates and return sorted list.

    Uses keyword matching as a baseline, and optionally LLM scoring
    for more nuanced evaluation.
    """
    candidates: list[ScoredCandidate] = []

    for username, profile in profiles.items():
        # Keyword-based pre-scoring
        kw_score, kw_matched = score_with_keywords(profile, persona)

        # Skip if no keyword match at all and no LLM available
        if kw_score == 0 and not anthropic_api_key:
            continue

        if anthropic_api_key:
            try:
                llm_result = score_with_llm(profile, persona, anthropic_api_key)
                rank = Rank(llm_result["rank"])
                score = llm_result["score"]
                match_reasons = llm_result["match_reasons"]
                matched_keywords = llm_result["matched_keywords"]
                potential_notes = llm_result["potential_notes"]
            except Exception as e:
                print(f"  [Warning] LLM scoring failed for @{username}: {e}")
                # Fallback to keyword scoring
                rank, score, match_reasons, matched_keywords, potential_notes = (
                    _fallback_scoring(kw_score, kw_matched)
                )
        else:
            rank, score, match_reasons, matched_keywords, potential_notes = (
                _fallback_scoring(kw_score, kw_matched)
            )

        # Apply location bonus
        if persona.location and persona.location.lower() in profile.bio.lower():
            score = min(score + 5, 100)
            match_reasons.append(f"希望エリア「{persona.location}」に合致")

        # Apply follower filter
        if persona.min_followers > 0 and profile.followers_count < persona.min_followers:
            score = max(score - 10, 0)

        candidates.append(
            ScoredCandidate(
                profile=profile,
                rank=rank,
                score=score,
                match_reasons=match_reasons,
                matched_keywords=matched_keywords,
                potential_notes=potential_notes,
            )
        )

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Re-assign ranks based on final scores
    for c in candidates:
        if c.score >= 70:
            c.rank = Rank.A
        elif c.score >= 40:
            c.rank = Rank.B
        else:
            c.rank = Rank.C

    return candidates


def _fallback_scoring(
    kw_score: int, kw_matched: list[str]
) -> tuple[Rank, int, list[str], list[str], str]:
    """Fallback scoring when LLM is not available."""
    score = min(kw_score, 100)

    if score >= 70:
        rank = Rank.A
    elif score >= 40:
        rank = Rank.B
    else:
        rank = Rank.C

    matched_keywords = [m.split("] ")[1] for m in kw_matched if "] " in m]
    match_reasons = [f"キーワード「{m}」がプロフィール/ツイートにマッチ" for m in matched_keywords]
    potential_notes = "キーワードベースの評価（LLM未使用）"

    return rank, score, match_reasons, matched_keywords, potential_notes
