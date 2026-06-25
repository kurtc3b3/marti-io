"""Health and metadata routes."""

from fastapi import APIRouter, Depends

from agents.checkpointer import get_checkpointer
from agents.redis_client import redis_health
from agents.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(settings: Settings = Depends(get_settings)) -> dict:
    postgres_ok: bool | None = None
    if settings.checkpointer == "postgres":
        try:
            get_checkpointer()
            postgres_ok = True
        except Exception:
            postgres_ok = False

    redis_ok = await redis_health()

    checks = [redis_ok]
    if postgres_ok is not None:
        checks.append(postgres_ok)
    status = "ok" if all(checks) else "degraded"

    return {
        "status": status,
        "checkpointer": settings.checkpointer,
        "postgres": postgres_ok,
        "redis": redis_ok,
    }


@router.get("/info")
async def info(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "docs_enabled": settings.expose_docs,
        "checkpointer": settings.checkpointer,
        "chat_transport": "websocket",
    }
