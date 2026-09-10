from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable

from utils.helpers import parse_datetime


def compute_relevance_score(tweet: Dict, priority_people: Iterable[str]) -> float:
    matches = tweet.get("matches", [])
    engagement = (
        int(tweet.get("likeCount", 0) or 0)
        + int(tweet.get("retweetCount", 0) or 0) * 2
        + int(tweet.get("replyCount", 0) or 0) * 2
        + int(tweet.get("quoteCount", 0) or 0) * 2
    )

    score = 20.0 if matches else 0.0
    score += max(0, len(matches) - 1) * 8.0
    score += min(engagement / 10.0, 25.0)

    author_name = (tweet.get("author", {}) or {}).get("name", "")
    author_username = (tweet.get("author", {}) or {}).get("userName", "")
    people_groups = {item["group"] for item in matches if item["match_type"] == "person"}
    priority_people = set(priority_people)
    if people_groups & priority_people or author_name in priority_people or author_username in priority_people:
        score += 10.0

    created_at = parse_datetime(tweet.get("createdAt"))
    if created_at:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_hours = max((datetime.now(timezone.utc) - created_at).total_seconds() / 3600, 0.0)
        score += max(0.0, 20.0 - min(age_hours / 6.0, 20.0))
    return round(score, 2)


def compute_risk_score(tweet: Dict) -> float:
    base = len(tweet.get("risk_terms", [])) * 18.0
    if tweet.get("is_chile_context"):
        base += 10.0
    text = (tweet.get("normalized_text") or "")
    if "fiscalizacion" in text or "sanciones" in text:
        base += 10.0
    return round(min(base, 100.0), 2)


def enrich_scores(tweet: Dict, catalog: dict) -> Dict:
    tweet["relevance_score"] = compute_relevance_score(tweet, catalog["priority_people"])
    tweet["risk_score"] = compute_risk_score(tweet)
    return tweet
