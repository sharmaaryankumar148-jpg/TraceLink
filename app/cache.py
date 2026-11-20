# Redis job queue (LPUSH / BRPOP) + stats cache.
# If redis isn't configured or reachable, callers fall back to inline processing.
import json
import logging

from app.config import settings

log = logging.getLogger(__name__)

QUEUE_KEY = "tracelink:jobs"
STATS_KEY = "tracelink:stats"

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client
    if settings.queue_mode != "redis":
        return None
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _client = client
    except Exception as exc:
        log.warning("Redis unavailable (%s), processing inline", exc)
        return None
    return _client


def set_client(client) -> None:
    global _client
    _client = client


def enqueue(complaint_id: int) -> bool:
    client = get_client()
    if client is None:
        return False
    client.lpush(QUEUE_KEY, complaint_id)
    return True


def dequeue(timeout: int = 5) -> int | None:
    client = get_client()
    if client is None:
        return None
    item = client.brpop(QUEUE_KEY, timeout=timeout)
    return int(item[1]) if item else None


def queue_length() -> int | None:
    client = get_client()
    return client.llen(QUEUE_KEY) if client is not None else None


def get_cached_stats() -> dict | None:
    client = get_client()
    if client is None:
        return None
    raw = client.get(STATS_KEY)
    return json.loads(raw) if raw else None


def set_cached_stats(stats: dict) -> None:
    client = get_client()
    if client is not None:
        client.set(STATS_KEY, json.dumps(stats, default=str), ex=settings.stats_cache_seconds)


def invalidate_stats() -> None:
    client = get_client()
    if client is not None:
        client.delete(STATS_KEY)
