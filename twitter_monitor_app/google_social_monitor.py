from __future__ import annotations

import argparse
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("google_social_monitor")

# URLs de APIs de Respaldo
GOOGLE_SEARCH_URL = "https://www.google.com/search"
SERPER_API_URL = "https://google.serper.dev/search"
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
GOOGLE_OFFICIAL_API_URL = "https://www.googleapis.com/customsearch/v1"

DEFAULT_KEYWORDS = ["Andess", "agua potable", "APR", "servicios sanitarios", "Aguas Andinas"]
MAX_GOOGLE_PAGES_PER_KEYWORD = 20
DEFAULT_GOOGLE_BACKOFF_SECONDS = 30.0
GOOGLE_KEYWORDS_BATCH_SIZE = 5


class GoogleRateLimitError(RuntimeError):
    pass

DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}\s+de\s+[a-zÃ¡Ã©Ã­Ã³ÃºÃ±]+(?:\s+de\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:ene|feb|mar|abr|may|jun|jul|ago|sept?|oct|nov|dic)\.?\s+\d{1,2},?\s+\d{4})\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PlatformConfig:
    name: str
    search_site: str
    allowed_url_fragments: tuple[str, ...]
    default_output_csv: str
    default_output_excel: str


PLATFORM_CONFIG = {
    "linkedin": PlatformConfig(
        name="linkedin",
        search_site="site:linkedin.com",
        allowed_url_fragments=("linkedin.com/posts", "linkedin.com/feed/update", "linkedin.com/pulse", "linkedin.com/company/", "linkedin.com/in/"),
        default_output_csv="linkedin_scraping_results.csv",
        default_output_excel="linkedin_scraping_results.xlsx",
    ),
    "x": PlatformConfig(
        name="x",
        search_site="site:x.com/status OR site:twitter.com/status",
        allowed_url_fragments=("/status/",),
        default_output_csv="x_google_scraping_results.csv",
        default_output_excel="x_google_scraping_results.xlsx",
    ),
}


def build_session(timeout: int = 20) -> Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
    session.request_timeout = timeout
    return session


def chunk_list(data: list, size: int):
    for i in range(0, len(data), size): yield data[i : i + size]


def build_google_query(keywords: list[str], platform: PlatformConfig) -> str:
    joined = " OR ".join(f'"{kw}"' for kw in keywords)
    return f'{platform.search_site} ({joined})'


def attribute_best_keyword(title: str, snippet: str, keywords: list[str]) -> str:
    text = f"{title} {snippet}".lower()
    for kw in keywords:
        if kw.lower() in text: return kw
    return keywords[0]


def is_allowed_result(url: str, platform: PlatformConfig) -> bool:
    normalized = (url or "").lower()
    return any(fragment in normalized for fragment in platform.allowed_url_fragments) if normalized.startswith("http") else False


# --- MÃ‰TODOS DE API ---

def fetch_serper_results(session: Session, api_key: str, query: str, num: int) -> list[dict]:
    """Plan A: Serper.dev (2.5k gratis)"""
    try:
        res = session.post(SERPER_API_URL, headers={"X-API-KEY": api_key, "Content-Type": "application/json"}, 
                           json={"q": query, "num": num, "gl": "cl", "hl": "es"}, timeout=30)
        res.raise_for_status()
        return [{"title": i.get("title", ""), "link": i.get("link", ""), "snippet": i.get("snippet", ""), "date": i.get("date", "")} for i in res.json().get("organic", [])]
    except Exception as e:
        logger.error("Error Serper: %s", e)
        return []

def fetch_google_official_results(session: Session, api_key: str, cx: str, query: str, num: int) -> list[dict]:
    """Plan B: Google Custom Search API (100 gratis/dÃ­a)"""
    try:
        res = session.get(GOOGLE_OFFICIAL_API_URL, params={"key": api_key, "cx": cx, "q": query, "num": num, "gl": "cl", "hl": "es"}, timeout=30)
        res.raise_for_status()
        return [{"title": i.get("title", ""), "link": i.get("link", ""), "snippet": i.get("snippet", ""), "date": ""} for i in res.json().get("items", [])]
    except Exception as e:
        logger.error("Error Google Official API: %s", e)
        return []

def fetch_searchapi_results(session: Session, api_key: str, query: str, num: int) -> list[dict]:
    """Plan C: SearchAPI.io (100 gratis totales)"""
    try:
        res = session.get(SEARCHAPI_URL, params={"engine": "google", "q": query, "api_key": api_key, "num": num, "gl": "cl", "hl": "es"}, timeout=30)
        res.raise_for_status()
        return [{"title": i.get("title", ""), "link": i.get("link", ""), "snippet": i.get("snippet", ""), "date": i.get("date", "")} for i in res.json().get("organic_results", [])]
    except Exception as e:
        logger.error("Error SearchAPI: %s", e)
        return []


def search_keywords_batch(session: Session, keywords: list[str], results_per_batch: int, language: str, platform: PlatformConfig) -> list[dict]:
    query = build_google_query(keywords, platform)
    raw_results = []
    method_used = "Ninguno"

    # Prioridad 1: Serper.dev
    if serper_key := os.environ.get("SERPER_API_KEY"):
        raw_results = fetch_serper_results(session, serper_key, query, results_per_batch)
        if raw_results: method_used = "Serper.dev"

    # Prioridad 2: Google Official
    if not raw_results and (g_key := os.environ.get("GOOGLE_API_KEY")) and (g_cx := os.environ.get("GOOGLE_CX")):
        raw_results = fetch_google_official_results(session, g_key, g_cx, query, results_per_batch)
        if raw_results: method_used = "Google Official API"

    # Prioridad 3: SearchAPI.io
    if not raw_results and (sapi_key := os.environ.get("SEARCHAPI_API_KEY")):
        raw_results = fetch_searchapi_results(session, sapi_key, query, results_per_batch)
        if raw_results: method_used = "SearchAPI.io"

    # Prioridad 4: Scraping (Sin API Key)
    if not raw_results:
        logger.warning("Sin API Keys vÃ¡lidas o resultados. Usando scraping como Ãºltimo recurso.")
        # AquÃ­ irÃ­a la lÃ³gica de scraping anterior simplificada
        return [] 

    logger.info("MÃ©todo exitoso: %s para lote %s", method_used, keywords[:2])
    
    collected = []
    for res in raw_results:
        if not is_allowed_result(res["link"], platform): continue
        best_kw = attribute_best_keyword(res["title"], res["snippet"], keywords)
        collected.append({
            "platform": platform.name, "keyword": best_kw, "titulo": res["title"], "descripcion": res["snippet"],
            "link": res["link"], "fecha": res.get("date") or "",
            "relevancia_score": score_result(best_kw, res["title"], res["snippet"], res["link"])
        })
    return collected


def score_result(keyword: str, title: str, snippet: str, url: str) -> int:
    k = keyword.lower()
    score = 0
    if k in (title or "").lower(): score += 1
    if k in (snippet or "").lower(): score += 1
    if k in (url or "").lower(): score += 1
    return score


def collect_monitor_results(
    keywords: list[str],
    results_per_keyword: int,
    language: str,
    platform_name: str,
    lowercase_text: bool,
    min_delay_seconds: float = 0.0,
    max_delay_seconds: float = 0.0,
) -> pd.DataFrame:
    platform = PLATFORM_CONFIG[platform_name]
    session = build_session()
    all_results = []
    batches = list(chunk_list([k.strip() for k in keywords if k.strip()], GOOGLE_KEYWORDS_BATCH_SIZE))
    
    for index, batch in enumerate(batches):
        all_results.extend(search_keywords_batch(session, batch, max(results_per_keyword, 30), language, platform))
        if index < len(batches) - 1 and max_delay_seconds > 0:
            time.sleep(random.uniform(min_delay_seconds, max_delay_seconds))
    
    df = pd.DataFrame(all_results)
    if df.empty: return pd.DataFrame(columns=["platform", "keyword", "titulo", "descripcion", "link", "fecha", "relevancia_score", "execution_timestamp"])
    
    df = df.drop_duplicates(subset=["keyword", "link"]).copy()
    if lowercase_text:
        for col in ("titulo", "descripcion"): df[col] = df[col].fillna("").str.lower()
    df["execution_timestamp"] = datetime.now(timezone.utc).isoformat()
    return df.sort_values(by=["keyword", "relevancia_score"], ascending=[True, False]).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    parser.add_argument("--platform", default="linkedin")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    df = collect_monitor_results(args.keywords, 20, "es", args.platform, False)
    print(df)


if __name__ == "__main__": main()
