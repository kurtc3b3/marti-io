"""Async Redis pool (optional — multi-instance WebSocket fan-out)."""

from __future__ import annotations

from redis.asyncio import Redis

from agents.settings import Settings, get_settings

_redis: Redis | None = None


async def init_redis(settings: Settings) -> Redis | None:
    global _redis
    if not settings.redis_enabled:
        return None

    _redis = Redis.from_url(
        settings.redis_url,  # type: ignore[arg-type]
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis.ping()
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError(
            "Redis not initialized — set REDIS_URL or call init_redis() at startup"
        )
    return _redis


async def shutdown_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def redis_health() -> bool | None:
    """Return ping result when Redis is configured, else None (disabled)."""
    settings = get_settings()
    if not settings.redis_enabled:
        return None

    try:
        redis = get_redis()
        return await redis.ping()
    except Exception:
        return False
