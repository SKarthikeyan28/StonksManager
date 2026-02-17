import json
import logging
from datetime import date

import redis

from src.config import settings

logger = logging.getLogger(__name__)

# Single Redis connection used across the service.
# decode_responses=True means we get Python strings back instead of raw bytes,
# so we don't have to call .decode() on every read.
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def _make_key(symbol: str) -> str:
    """
    Build a namespaced Redis key like 'stock:AAPL:ohlcv'.
    Namespacing prevents collisions — later, sentiment results might use
    'stock:AAPL:sentiment' in the same Redis instance.
    """
    return f"stock:{symbol.upper()}:ohlcv"


def _serialize_record(record: dict) -> dict:
    """
    Convert a single OHLCV record to JSON-safe format.
    date objects aren't JSON-serializable, so we convert to ISO string.
    """
    serialized = record.copy()
    if isinstance(serialized.get("date"), date):
        serialized["date"] = serialized["date"].isoformat()
    return serialized


def _deserialize_record(record: dict) -> dict:
    """Reverse of _serialize_record — convert ISO date string back to date object."""
    deserialized = record.copy()
    if isinstance(deserialized.get("date"), str):
        deserialized["date"] = date.fromisoformat(deserialized["date"])
    return deserialized


def cache_ohlcv(symbol: str, records: list[dict]) -> None:
    """
    Store OHLCV data in Redis with a TTL (time-to-live).

    After CACHE_TTL seconds (default 1 hour), Redis automatically deletes
    the key. This ensures other services always get reasonably fresh data
    without us needing manual cache invalidation logic.
    """
    key = _make_key(symbol)
    serialized = [_serialize_record(r) for r in records]
    redis_client.setex(key, settings.CACHE_TTL, json.dumps(serialized))
    logger.info(f"Cached {len(records)} OHLCV records for {symbol} (TTL={settings.CACHE_TTL}s)")


def get_cached_ohlcv(symbol: str) -> list[dict] | None:
    """
    Retrieve cached OHLCV data. Returns None on cache miss.

    Other services (technical, forecast) call this to read price data
    without hitting PostgreSQL directly.
    """
    key = _make_key(symbol)
    raw = redis_client.get(key)

    if raw is None:
        logger.debug(f"Cache miss for {symbol}")
        return None

    records = [_deserialize_record(r) for r in json.loads(raw)]
    logger.debug(f"Cache hit for {symbol}: {len(records)} records")
    return records
