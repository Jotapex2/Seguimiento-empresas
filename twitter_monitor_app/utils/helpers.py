from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Iterable, List


def chunk_list(items: List[str], chunk_size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def ensure_utc_bounds(start_date: date | None, end_date: date | None) -> tuple[int | None, int | None]:
    start_ts = None
    end_ts = None
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        start_ts = int(start_dt.timestamp())
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        end_ts = int(end_dt.timestamp())
    return start_ts, end_ts


def safe_divide(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator
