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

from rozkoduj_mcp.auth import trusted_client_ip

_SKIP_PATHS: frozenset[str] = frozenset({"/health", "/robots.txt"})

# Longest inbound trace value worth echoing back onto an outbound request.
# Both formats this understands are far shorter; anything else is a caller
# putting arbitrary bytes in a header we forward.
_MAX_TRACE_LENGTH = 200


def _forwardable(value: str) -> str | None:
    """Return the value only if it can safely go back onto the wire.

    Starlette decodes inbound headers as latin-1, so a client can put bytes in
    here that the outbound client cannot encode. Forwarding one raised a bare
    UnicodeEncodeError out of every tool call in that request - self-inflicted,
    but it surfaced as an unactionable error instead of being ignored. Control
    characters are refused for the same reason a header value should never
    carry them.
    """
    if len(value) > _MAX_TRACE_LENGTH or not value.isascii() or not value.isprintable():
        return None
    return value


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
        return cloud.split("/", 1)[0] or None, _forwardable(cloud)
    w3c = request.headers.get("traceparent")
    if w3c:
        parts = w3c.split("-")
        if len(parts) >= 2 and parts[1]:
            return parts[1], _forwardable(w3c)
    return None, None


def _client_ip(request: Request) -> str | None:
    """The caller's address, not the proxy that delivered the request.

    Behind Cloud Run ``request.client`` is the platform frontend, so every
    entry recorded the same link-local address and the field said nothing about
    who called. These logs are the only per-request record this server keeps, so
    the field has to name the caller or it is not worth writing. Falls back to
    the socket peer when there is no proxy in front, which is the local case.
    """
    forwarded = request.headers.getlist("x-forwarded-for")
    if forwarded:
        trusted = trusted_client_ip(",".join(forwarded))
        if trusted:
            return trusted
    return request.client.host if request.client else None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as structured JSON to stdout."""

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
                "ip": _client_ip(request),
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
