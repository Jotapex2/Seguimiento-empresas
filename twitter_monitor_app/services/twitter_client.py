from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import get_settings
from utils.helpers import ensure_utc_bounds, parse_datetime

logger = logging.getLogger(__name__)


class TwitterApiError(RuntimeError):
    pass


class TwitterClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.api_key
        self.base_url = (base_url or self.settings.base_url).rstrip("/")
        self.session = requests.Session()
        retry = Retry(
            total=self.settings.max_retries,
            backoff_factor=self.settings.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TwitterApiError("TWITTERAPI_IO_KEY no configurada.")
        return {"x-api-key": self.api_key}

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(
            url,
            headers=self._headers(),
            params=params or {},
            timeout=self.settings.request_timeout,
        )
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "2"))
            logger.warning("Rate limit alcanzado. Reintentando en %s segundos.", retry_after)
            time.sleep(retry_after)
        if response.status_code >= 400:
            logger.error("Error HTTP %s en %s: %s", response.status_code, endpoint, response.text[:500])
            raise TwitterApiError(f"Error HTTP {response.status_code} al consultar {endpoint}")
        payload = response.json()
        if payload.get("status") == "error":
            message = payload.get("message") or payload.get("msg") or "Error desconocido"
            logger.error("Error de API en %s: %s", endpoint, message)
            raise TwitterApiError(message)
        return payload

    def _paginate(
        self, 
        endpoint: str, 
        params: Dict, 
        result_key: str, 
        max_results: int,
        stop_condition: Callable[[List[Dict]], bool] | None = None
    ) -> List[Dict]:
        results: List[Dict] = []
        cursor = ""
        empty_page_hits = 0

        while len(results) < max_results:
            current_params = {**params, "cursor": cursor}
            payload = self._request(endpoint, current_params)
            page_items = payload.get(result_key, []) or []

            if not page_items:
                empty_page_hits += 1
                if empty_page_hits >= 1:
                    break
            else:
                results.extend(page_items)
                
            if stop_condition and stop_condition(page_items):
                # Cut early to save API calls if we hit old tweets
                break

            has_next = payload.get("has_next_page", False)
            next_cursor = payload.get("next_cursor") or ""
            if not has_next or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        return results[:max_results]

    def search_tweets(
        self,
        query: str,
        max_results: int = 40,
        start_date=None,
        end_date=None,
        query_type: str = "Latest",
        since_time: int | None = None,
        until_time: int | None = None,
    ) -> List[Dict]:
        params: Dict[str, object] = {
            "query": query,
            "queryType": query_type,
        }
        start_ts, end_ts = ensure_utc_bounds(start_date, end_date)
        if since_time is not None:
            start_ts = since_time
        if until_time is not None:
            end_ts = until_time
        if start_ts:
            params["sinceTime"] = start_ts
        if end_ts:
            params["untilTime"] = end_ts
        return self._paginate("/twitter/tweet/advanced_search", params, "tweets", max_results=max_results)

    def get_user_tweets(
        self, 
        username: str, 
        max_results: int = 40, 
        include_replies: bool = False,
        since_time: int | None = None
    ) -> List[Dict]:
        params = {
            "userName": username.lstrip("@"),
            "includeReplies": str(include_replies).lower(),
        }
        
        def stop_on_old_tweets(page_items: List[Dict]) -> bool:
            if not since_time:
                return False
            for tweet in page_items:
                created_at = parse_datetime(tweet.get("createdAt"))
                if created_at and int(created_at.timestamp()) < since_time:
                    return True
            return False
            
        return self._paginate(
            "/twitter/user/last_tweets", 
            params, 
            "tweets", 
            max_results=max_results,
            stop_condition=stop_on_old_tweets
        )
