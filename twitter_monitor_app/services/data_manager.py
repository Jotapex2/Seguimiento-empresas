from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from services.query_builder import append_date_operators, build_query_plan
from services.runtime_store import (
    load_cache,
    load_incremental_state,
    make_cache_key,
    save_cache,
    update_incremental_state,
)
from services.twitter_client import TwitterApiError, TwitterClient
from utils.helpers import parse_datetime


def mock_tweets() -> List[Dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "1",
            "url": "https://x.com/example/status/1",
            "text": "Aguas Andinas y Andess advierten sobre sequía y riesgo de racionamiento en Chile central.",
            "createdAt": (now - timedelta(hours=2)).isoformat(),
            "lang": "es",
            "likeCount": 18,
            "retweetCount": 7,
            "replyCount": 4,
            "quoteCount": 1,
            "viewCount": 1500,
            "author": {"name": "Radio Sectorial", "userName": "radiosectorial"},
        },
        {
            "id": "2",
            "url": "https://x.com/example/status/2",
            "text": "La SISS inició fiscalización por tarifas y sanciones a empresa sanitaria en la región del Biobío.",
            "createdAt": (now - timedelta(hours=12)).isoformat(),
            "lang": "es",
            "likeCount": 28,
            "retweetCount": 10,
            "replyCount": 6,
            "quoteCount": 3,
            "viewCount": 4200,
            "author": {"name": "Prensa Regulatoria", "userName": "prensareg"},
        },
        {
            "id": "3",
            "url": "https://x.com/example/status/3",
            "text": "Nuevo debate sobre agua potable rural, APR y cambio climático en Chile.",
            "createdAt": (now - timedelta(days=1)).isoformat(),
            "lang": "es",
            "likeCount": 11,
            "retweetCount": 4,
            "replyCount": 2,
            "quoteCount": 0,
            "viewCount": None,
            "author": {"name": "Observatorio Hídrico", "userName": "obs_hidrico"},
        },
        {
            "id": "4",
            "url": "https://x.com/example/status/4",
            "text": "ESSBIO anuncia inversión en saneamiento y seguridad hídrica.",
            "createdAt": (now - timedelta(days=2)).isoformat(),
            "lang": "es",
            "likeCount": 8,
            "retweetCount": 2,
            "replyCount": 1,
            "quoteCount": 0,
            "viewCount": 900,
            "author": {"name": "Diario Regional", "userName": "diarioregional"},
        },
    ]


def get_strategy_profile(strategy: str, requested_limit: int) -> Dict[str, int]:
    if strategy == "Rápida":
        return {"effective_limit": min(requested_limit, 200), "max_batches": 6, "timeline_limit": 10, "min_per_query": 20}
    if strategy == "Profunda":
        return {"effective_limit": requested_limit, "max_batches": 9999, "timeline_limit": 40, "min_per_query": 50}
    return {"effective_limit": min(requested_limit, 1000), "max_batches": 20, "timeline_limit": 20, "min_per_query": 20}


def prioritize_query_plan(query_plan: List[Dict], strategy: str) -> List[Dict]:
    ordered = sorted(
        query_plan,
        key=lambda item: (
            0 if item["category"] in {"Personas", "Empresas"} else 1,
            len(item["query"]),
        ),
    )
    max_batches = get_strategy_profile(strategy, 0)["max_batches"]
    return ordered[:max_batches]


def newest_created_at(tweets: List[Dict]) -> str | None:
    timestamps = [tweet.get("createdAt") for tweet in tweets if tweet.get("createdAt")]
    return max(timestamps) if timestamps else None


def collect_api_data(filters: Dict, catalog: dict) -> tuple[List[Dict], Dict]:
    client = TwitterClient()
    collected: List[Dict] = []
    query_plan = build_query_plan(
        filters["selected_categories"],
        filters["selected_people"],
        filters["selected_companies"],
        catalog,
    )
    strategy_profile = get_strategy_profile(filters["strategy"], filters["limit"])
    query_plan = prioritize_query_plan(query_plan, filters["strategy"])
    incremental_state = load_incremental_state()
    stats = {
        "api_calls_saved_by_cache": 0,
        "query_batches_planned": len(query_plan),
        "query_batches_executed": 0,
        "timeline_users_executed": 0,
        "effective_limit": strategy_profile["effective_limit"],
        "stopped_early": False,
    }

    if not client.enabled:
        raise TwitterApiError("No hay API key configurada. Activa simulación o define TWITTERAPI_IO_KEY.")

    if not query_plan and not filters["selected_monitor_users"]:
        raise TwitterApiError("Selecciona al menos una categoría, persona, empresa o timeline para ejecutar el monitoreo.")

    per_query_limit = max(
        strategy_profile["min_per_query"],
        strategy_profile["effective_limit"] // max(len(query_plan), 1),
    )

    for item in query_plan:
        query = append_date_operators(item["query"], filters["start_date"], filters["end_date"])
        state_key = make_cache_key("incremental", {"query": query, "category": item["category"]})
        since_time = None
        if filters["incremental_mode"]:
            last_seen = incremental_state.get(state_key)
            parsed = parse_datetime(last_seen)
            if parsed:
                since_time = int(parsed.timestamp()) + 1

        cache_payload = {
            "mode": "search",
            "query": query,
            "max_results": per_query_limit,
            "start_date": filters["start_date"],
            "end_date": filters["end_date"],
            "since_time": since_time,
            "strategy": filters["strategy"],
        }
        cache_key = make_cache_key("search", cache_payload)
        tweets = load_cache(cache_key, filters["cache_ttl_hours"]) if filters["use_cache"] else None
        if tweets is None:
            tweets = client.search_tweets(
                query=query,
                max_results=per_query_limit,
                start_date=filters["start_date"],
                end_date=filters["end_date"],
                since_time=since_time,
            )
            if filters["use_cache"]:
                save_cache(cache_key, tweets)
        else:
            stats["api_calls_saved_by_cache"] += 1

        for tweet in tweets:
            tweet["query_batch"] = item["query"]
            tweet["query_category"] = item["category"]
        collected.extend(tweets)
        stats["query_batches_executed"] += 1
        update_incremental_state(state_key, newest_created_at(tweets))

        if len(collected) >= strategy_profile["effective_limit"]:
            stats["stopped_early"] = True
            break

    if filters["include_user_timelines"]:
        remaining_capacity = max(strategy_profile["effective_limit"] - len(collected), 0)
        timeline_limit = min(strategy_profile["timeline_limit"], remaining_capacity) if remaining_capacity else 0

        for username in filters["selected_monitor_users"]:
            if not timeline_limit:
                stats["stopped_early"] = True
                break

            state_key = make_cache_key("incremental", {"timeline": username})
            since_time = None
            if filters["incremental_mode"]:
                last_seen = incremental_state.get(state_key)
                parsed = parse_datetime(last_seen)
                if parsed:
                    since_time = int(parsed.timestamp()) + 1

            cache_payload = {
                "mode": "timeline",
                "username": username,
                "max_results": timeline_limit,
                "since_time": since_time,
            }
            cache_key = make_cache_key("timeline", cache_payload)
            tweets = load_cache(cache_key, filters["cache_ttl_hours"]) if filters["use_cache"] else None
            if tweets is None:
                tweets = client.get_user_tweets(username=username, max_results=timeline_limit, since_time=since_time)
                if filters["use_cache"]:
                    save_cache(cache_key, tweets)
            else:
                stats["api_calls_saved_by_cache"] += 1

            for tweet in tweets:
                tweet["query_batch"] = f"user:{username}"
                tweet["query_category"] = "Timeline"
            collected.extend(tweets)
            stats["timeline_users_executed"] += 1
            update_incremental_state(state_key, newest_created_at(tweets))

            remaining_capacity = max(strategy_profile["effective_limit"] - len(collected), 0)
            timeline_limit = min(strategy_profile["timeline_limit"], remaining_capacity) if remaining_capacity else 0
            if len(collected) >= strategy_profile["effective_limit"]:
                stats["stopped_early"] = True
                break

    return collected[: strategy_profile["effective_limit"]], stats
