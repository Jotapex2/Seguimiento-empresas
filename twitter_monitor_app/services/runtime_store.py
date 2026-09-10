from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

from config.settings import get_settings


def _runtime_dir() -> Path:
    path = get_settings().runtime_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_dir() -> Path:
    path = _runtime_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_file() -> Path:
    return _runtime_dir() / "incremental_state.json"


def _history_file() -> Path:
    return _runtime_dir() / "history.json"


def make_cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return f"{prefix}_{sha256(canonical.encode('utf-8')).hexdigest()}"


def load_cache(key: str, ttl_hours: int) -> Any | None:
    cache_file = _cache_dir() / f"{key}.json"
    if not cache_file.exists():
        return None
    with cache_file.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    cached_at = datetime.fromisoformat(payload["cached_at"])
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
        return None
    return payload.get("data")


def save_cache(key: str, data: Any) -> None:
    cache_file = _cache_dir() / f"{key}.json"
    payload = {"cached_at": datetime.now(timezone.utc).isoformat(), "data": data}
    with cache_file.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def load_incremental_state() -> Dict[str, str]:
    state_file = _state_file()
    if not state_file.exists():
        return {}
    with state_file.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_incremental_state(state: Dict[str, str]) -> None:
    with _state_file().open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def update_incremental_state(query_key: str, newest_created_at: str | None) -> None:
    if not newest_created_at:
        return
    state = load_incremental_state()
    current_value = state.get(query_key)
    if current_value and current_value >= newest_created_at:
        return
    state[query_key] = newest_created_at
    save_incremental_state(state)


def persist_history(tweets: List[Dict[str, Any]]) -> int:
    history_file = _history_file()
    existing: Dict[str, Dict[str, Any]] = {}
    if history_file.exists():
        with history_file.open("r", encoding="utf-8") as fh:
            for item in json.load(fh):
                tweet_id = str(item.get("id") or "")
                if tweet_id:
                    existing[tweet_id] = item

    for tweet in tweets:
        tweet_id = str(tweet.get("id") or "")
        if tweet_id:
            existing[tweet_id] = tweet

    merged = list(existing.values())
    with history_file.open("w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    return len(merged)


def get_history_count() -> int:
    history_file = _history_file()
    if not history_file.exists():
        return 0
    with history_file.open("r", encoding="utf-8") as fh:
        return len(json.load(fh))
