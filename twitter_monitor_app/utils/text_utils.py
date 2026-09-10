import re
import unicodedata
from typing import Iterable, List


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    cleaned = strip_accents((text or "").lower())
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[@#]\w+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def contains_any_term(text: str, terms: Iterable[str]) -> bool:
    normalized_text = f" {normalize_text(text)} "
    return any(f" {normalize_text(term)} " in normalized_text for term in terms)


def find_matching_terms(text: str, terms: Iterable[str]) -> List[str]:
    normalized_text = f" {normalize_text(text)} "
    matches = []
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and f" {normalized_term} " in normalized_text:
            matches.append(term)
    return matches


def looks_spanish(tweet: dict) -> bool:
    lang = (tweet.get("lang") or "").lower()
    if lang == "es":
        return True

    text = normalize_text(tweet.get("text", ""))
    spanish_signals = [
        " el ",
        " la ",
        " de ",
        " que ",
        " agua ",
        " chile ",
        " servicio ",
    ]
    padded = f" {text} "
    score = sum(1 for token in spanish_signals if token in padded)
    return score >= 2
