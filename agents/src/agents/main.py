"""Run the Daily Agent Hub API with uvicorn."""

from __future__ import annotations

import uvicorn

from agents.settings import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "agents.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    run()
