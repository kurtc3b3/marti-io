"""Structured logging with optional JSON output and payload redaction."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from agents.settings import Settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "openai_api_key",
        "access_token",
        "refresh_token",
    }
)

_NOISY_WS_EVENTS = frozenset({"token"})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        if hasattr(record, "data"):
            payload["data"] = record.data
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        return True


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] [rid=%(request_id)s] %(message)s"
            )
        )

    root.addHandler(handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid4().hex[:12]


def set_request_id(request_id: str | None = None) -> str:
    rid = request_id or new_request_id()
    request_id_var.set(rid)
    return rid


def sanitize_payload(
    data: Any,
    *,
    max_length: int = 4000,
    max_depth: int = 6,
) -> Any:
    return _sanitize(data, depth=0, max_depth=max_depth, max_length=max_length)


def _sanitize(value: Any, *, depth: int, max_depth: int, max_length: int) -> Any:
    if depth > max_depth:
        return "<max_depth>"

    if isinstance(value, dict):
        return {
            key: (
                "<redacted>"
                if str(key).lower() in _SENSITIVE_KEYS
                else _sanitize(val, depth=depth + 1, max_depth=max_depth, max_length=max_length)
            )
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            _sanitize(item, depth=depth + 1, max_depth=max_depth, max_length=max_length)
            for item in value[:50]
        ]

    if isinstance(value, (str, bytes)):
        text = value.decode() if isinstance(value, bytes) else value
        if len(text) > max_length:
            return f"{text[:max_length]}…<{len(text)} chars>"
        return text

    return value


def log_payload(
    logger: logging.Logger,
    event: str,
    payload: Any | None = None,
    *,
    level: int = logging.INFO,
    **context: Any,
) -> None:
    data: dict[str, Any] = dict(context)
    if payload is not None:
        data["payload"] = sanitize_payload(payload)

    extra = {"event": event, "data": data}
    message = event
    if data:
        message = f"{event} {json.dumps(data, default=str)}"

    logger.log(level, message, extra=extra)


def ws_log_level(event_type: str, *, settings: Settings) -> int:
    if not settings.log_payloads:
        return logging.DEBUG
    if event_type in _NOISY_WS_EVENTS:
        return logging.DEBUG
    return logging.INFO
