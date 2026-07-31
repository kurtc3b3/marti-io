"""Run the Daily Agent Hub API with uvicorn."""

from __future__ import annotations

import uvicorn

from agents.settings import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run("agents.app:create_app", **settings.uvicorn_kwargs())


if __name__ == "__main__":
    run()
