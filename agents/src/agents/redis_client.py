"""Async Redis connection pool."""

from __future__ import annotations

from redis.asyncio import Redis

from agents.settings import Settings

_redis: Redis | None = None


async def init_redis(settings: Settings) -> Redis:
    global _redis
    _redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis.ping()
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized — call init_redis() at startup")
    return _redis


async def shutdown_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def redis_health() -> bool:
    try:
        redis = get_redis()
        return await redis.ping()
    except Exception:
        return False
