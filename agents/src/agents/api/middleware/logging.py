"""HTTP request/response logging middleware with payloads."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from agents.logging_setup import (
    get_logger,
    log_payload,
    new_request_id,
    request_id_var,
    sanitize_payload,
)
from agents.settings import get_settings

logger = get_logger("agents.http")

_SKIP_PATHS = frozenset({"/", "/favicon.ico"})
_SKIP_PREFIXES = ("/assets/",)


class PayloadLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if not settings.log_http_payloads:
            return await call_next(request)

        path = request.url.path
        if path in _SKIP_PATHS or path.startswith(_SKIP_PREFIXES):
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or new_request_id()
        token = request_id_var.set(request_id)
        started = time.perf_counter()

        body = await request.body()
        request_payload = _parse_json_body(body)
        request = Request(request.scope, receive=_make_receive(body))

        log_payload(
            logger,
            "http.request",
            {
                "method": request.method,
                "path": path,
                "query": dict(request.query_params),
                "client": request.client.host if request.client else None,
                "body": request_payload,
            },
            request_id=request_id,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_payload(
                logger,
                "http.error",
                {"method": request.method, "path": path, "duration_ms": duration_ms},
                level=logging.ERROR,
                request_id=request_id,
            )
            raise
        finally:
            request_id_var.reset(token)

        response_body, response = await _capture_response_body(response)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        log_payload(
            logger,
            "http.response",
            {
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "body": response_body,
            },
            request_id=request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def _make_receive(body: bytes):
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _parse_json_body(body: bytes) -> Any:
    if not body:
        return None
    try:
        return sanitize_payload(json.loads(body))
    except Exception:
        return "<unreadable>"


async def _capture_response_body(response: Response) -> tuple[Any, Response]:
    if response.status_code in {204, 304}:
        return None, response

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None, response

    body = getattr(response, "body", None)
    if not body:
        return None, response

    return _parse_json_body(body), response
