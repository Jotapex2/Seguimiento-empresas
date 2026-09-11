from __future__ import annotations

from typing import Dict, List

from twitter_monitor_app.utils.text_utils import contains_any_term, find_matching_terms, looks_spanish, normalize_text


def detect_chile_context(text: str, context_terms: List[str]) -> bool:
    return contains_any_term(text, context_terms)


def detect_chile_origin(tweet: Dict, context_terms: List[str]) -> bool:
    place = tweet.get("place") or {}
    author = tweet.get("author") or {}

    direct_country_signals = [
        place.get("countryCode"),
        place.get("country"),
        tweet.get("countryCode"),
        tweet.get("country"),
        author.get("location"),
    ]
    for signal in direct_country_signals:
        normalized_signal = normalize_text(str(signal or ""))
        if normalized_signal in {"cl", "chile"} or " chile " in f" {normalized_signal} ":
            return True

    combined_text = " ".join(
        [
            tweet.get("text", "") or "",
            place.get("fullName", "") or "",
            place.get("name", "") or "",
            author.get("location", "") or "",
        ]
    )
    return detect_chile_context(combined_text, context_terms)


def classify_tweet(tweet: Dict, catalog: dict) -> Dict:
    text = tweet.get("text", "")
    normalized = normalize_text(text)
    matches: List[Dict] = []

    for category, terms in catalog["sector_topics"].items():
        for term in find_matching_terms(normalized, terms):
            matches.append({"match_type": "category", "group": category, "term": term})

    for company, aliases in catalog["companies"].items():
        for term in find_matching_terms(normalized, aliases):
            matches.append({"match_type": "company", "group": company, "term": term})

    for person, aliases in catalog["people"].items():
        for term in find_matching_terms(normalized, aliases):
            matches.append({"match_type": "person", "group": person, "term": term})

    risk_matches = find_matching_terms(normalized, catalog["risk_terms"])
    for term in risk_matches:
        matches.append({"match_type": "risk", "group": "Riesgo reputacional", "term": term})

    category_detected = ", ".join(sorted({item["group"] for item in matches if item["match_type"] == "category"})) or "Sin categoría"
    first_keyword = matches[0]["term"] if matches else ""

    return {
        "normalized_text": normalized,
        "is_spanish": looks_spanish(tweet),
        "is_chile_context": detect_chile_context(normalized, catalog["chile_context_terms"]),
        "is_chile_origin": detect_chile_origin(tweet, catalog["chile_context_terms"]),
        "matches": matches,
        "category_detected": category_detected,
        "matched_keyword": first_keyword,
        "risk_terms": risk_matches,
    }


def post_process_tweets(
    tweets: List[Dict],
    catalog: dict,
    strict_keyword_filter: bool = True,
    chile_only: bool = False,
) -> List[Dict]:
    processed = []
    seen_ids = set()

    for tweet in tweets:
        tweet_id = tweet.get("id")
        if tweet_id in seen_ids:
            continue
        seen_ids.add(tweet_id)

        enriched = {**tweet, **classify_tweet(tweet, catalog)}
        if not enriched["is_spanish"]:
            continue
        if chile_only and not enriched["is_chile_origin"]:
            continue
        if strict_keyword_filter and not enriched["matches"]:
            continue
        processed.append(enriched)

    return processed
