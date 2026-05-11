"""Per-tool telemetry events fired to PostHog.

Wraps every tool registered via ``mcp.tool(...)`` with a thin async
decorator that emits one PostHog event per call - tool name, tier,
duration, ok/error. Identity is derived from the verified JWT in flight
(via ``current_token_string`` from auth.py); anonymous calls fire under
the IP-shaped distinct id so PostHog can still build a funnel.

No-op when ``POSTHOG_API_KEY`` is unset, so unit tests and local dev
stay quiet without extra configuration.
"""

import functools
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

import jwt
import posthog

from rozkoduj_mcp.auth import current_token_string

logger = logging.getLogger(__name__)

_EVENT = "mcp_tool_called"


def _configure_posthog_from_env() -> bool:
    """Initialize the PostHog client from environment. Idempotent."""
    api_key = os.environ.get("POSTHOG_API_KEY")
    if not api_key:
        return False
    posthog.api_key = api_key
    posthog.host = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")
    # Local dev shouldn't ship batched events.
    posthog.debug = os.environ.get("POSTHOG_DEBUG", "").lower() in ("1", "true", "yes")
    return True


_CONFIGURED = _configure_posthog_from_env()


def _identity_from_jwt() -> tuple[str | None, str]:
    """Extract (user_id, tier) from the bearer token bound to this request.

    The JWT is already verified upstream (FastMCP auth + our verifier), so
    a no-verify decode is safe and avoids a second JWKS roundtrip.
    """
    raw = current_token_string()
    if not raw:
        return None, "anon"
    try:
        payload: dict[str, Any] = jwt.decode(raw, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None, "free"
    sub = payload.get("sub")
    user_id = str(sub) if sub else None
    tier = str(payload.get("tier", "free"))
    return user_id, tier


def _capture(
    *,
    tool_name: str,
    user_id: str | None,
    tier: str,
    duration_ms: int,
    ok: bool,
    error_kind: str | None,
) -> None:
    if not _CONFIGURED:
        return
    distinct_id = user_id or f"anon:{tool_name}"
    try:
        posthog.capture(
            distinct_id=distinct_id,
            event=_EVENT,
            properties={
                "tool": tool_name,
                "tier": tier,
                "duration_ms": duration_ms,
                "ok": ok,
                "error_kind": error_kind,
                "authenticated": user_id is not None,
            },
        )
    except (ValueError, RuntimeError, OSError) as exc:
        logger.debug("posthog_capture_failed: %s", exc)


def with_telemetry[**P, R](
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Wrap an async tool function with PostHog per-call telemetry."""
    tool_name = func.__name__

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.monotonic()
        ok = True
        error_kind: str | None = None
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            ok = False
            error_kind = type(exc).__name__
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            user_id, tier = _identity_from_jwt()
            _capture(
                tool_name=tool_name,
                user_id=user_id,
                tier=tier,
                duration_ms=duration_ms,
                ok=ok,
                error_kind=error_kind,
            )

    return wrapper


def install_tool_telemetry(mcp_instance: Any) -> None:
    """Monkey-patch ``mcp_instance.tool`` so every registered tool is wrapped.

    Called once at server-build time. Existing ``@mcp.tool(...)`` decorations
    pick up the wrapper without any per-tool edits.
    """
    original_tool = mcp_instance.tool

    def tracked_tool[**P, R](
        *args: Any, **kwargs: Any
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        inner_decorator = original_tool(*args, **kwargs)

        def outer(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            wrapped = with_telemetry(func)
            registered = inner_decorator(wrapped)
            return registered  # type: ignore[no-any-return]

        return outer

    mcp_instance.tool = tracked_tool
