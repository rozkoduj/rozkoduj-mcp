"""Structured request logging middleware for Cloud Run."""

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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as structured JSON to stdout (parsed by Cloud Logging)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.url.path in _SKIP_PATHS:
            resp: Response = await call_next(request)
            return resp

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
            severity = "INFO" if status < 400 else "WARNING" if status < 500 else "ERROR"
            sys.stdout.write(
                json.dumps({"severity": severity, "message": "request", **entry}) + "\n"
            )
