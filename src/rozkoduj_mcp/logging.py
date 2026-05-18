"""Structured request logging middleware."""

import contextvars
import json
import sys
import time
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_SKIP_PATHS: frozenset[str] = frozenset({"/health", "/robots.txt"})

# Bound by the middleware so outbound calls can forward the same trace
# header and Cloud Logging joins entries across services on this id.
current_trace_header: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_trace_header", default=None
)


def _extract_trace_id(request: Request) -> tuple[str | None, str | None]:
    """Return (trace_id_for_logs, raw_header_to_forward).

    Prefers Cloud Run's ``X-Cloud-Trace-Context`` (auto-injected on the
    platform) and falls back to the W3C ``traceparent`` so local clients and
    other hosts still produce correlated logs.
    """
    cloud = request.headers.get("x-cloud-trace-context")
    if cloud:
        return cloud.split("/", 1)[0] or None, cloud
    w3c = request.headers.get("traceparent")
    if w3c:
        parts = w3c.split("-")
        if len(parts) >= 2 and parts[1]:
            return parts[1], w3c
    return None, None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as structured JSON to stdout."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        if request.url.path in _SKIP_PATHS:
            resp: Response = await call_next(request)
            return resp

        trace_id, raw_trace = _extract_trace_id(request)
        token = current_trace_header.set(raw_trace)
        start = time.monotonic()
        status = 500
        try:
            resp = await call_next(request)
            status = resp.status_code
            return resp
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            entry: dict[str, Any] = {
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": duration_ms,
                "ip": request.client.host if request.client else None,
                "ua": (request.headers.get("user-agent") or "")[:120],
            }
            if trace_id:
                entry["trace_id"] = trace_id
            severity = (
                "INFO" if status < 400 else "WARNING" if status < 500 else "ERROR"
            )
            sys.stdout.write(
                json.dumps({"severity": severity, "message": "request", **entry}) + "\n"
            )
            current_trace_header.reset(token)
