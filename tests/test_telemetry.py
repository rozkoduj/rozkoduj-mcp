"""Tests for rozkoduj_mcp.telemetry (per-tool PostHog events)."""

from collections.abc import Iterator
from unittest.mock import patch

import jwt as pyjwt
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from rozkoduj_mcp.telemetry import (
    _identity_from_jwt,
    install_tool_telemetry,
    with_telemetry,
)


def _bind_user(*, token: str) -> object:
    """Bind an AuthenticatedUser with the given raw token for the duration of a test."""
    user = AuthenticatedUser(AccessToken(token=token, client_id="cli", scopes=["mcp:read"]))
    return auth_context_var.set(user)


class TestIdentityFromJwt:
    def test_anonymous_returns_anon_tier(self) -> None:
        assert _identity_from_jwt() == (None, "anon")

    def test_decodes_sub_and_tier(self) -> None:
        token = pyjwt.encode({"sub": "user_xyz", "tier": "premium"}, "k" * 32, algorithm="HS256")
        reset = _bind_user(token=token)
        try:
            assert _identity_from_jwt() == ("user_xyz", "premium")
        finally:
            auth_context_var.reset(reset)

    def test_missing_tier_defaults_to_free(self) -> None:
        token = pyjwt.encode({"sub": "user_xyz"}, "k" * 32, algorithm="HS256")
        reset = _bind_user(token=token)
        try:
            assert _identity_from_jwt() == ("user_xyz", "free")
        finally:
            auth_context_var.reset(reset)


class TestWithTelemetry:
    @pytest.mark.anyio
    async def test_returns_value_and_fires_capture(self) -> None:
        @with_telemetry
        async def my_tool(x: int) -> int:
            return x * 2

        with patch("rozkoduj_mcp.telemetry._capture") as mock_capture:
            result = await my_tool(3)

        assert result == 6
        mock_capture.assert_called_once()
        kwargs = mock_capture.call_args.kwargs
        assert kwargs["tool_name"] == "my_tool"
        assert kwargs["ok"] is True
        assert kwargs["error_kind"] is None
        assert kwargs["tier"] == "anon"

    @pytest.mark.anyio
    async def test_records_failure_without_swallowing(self) -> None:
        @with_telemetry
        async def my_tool() -> None:
            raise ValueError("boom")

        with (
            patch("rozkoduj_mcp.telemetry._capture") as mock_capture,
            pytest.raises(ValueError),
        ):
            await my_tool()

        kwargs = mock_capture.call_args.kwargs
        assert kwargs["ok"] is False
        assert kwargs["error_kind"] == "ValueError"


class TestInstallToolTelemetry:
    def test_wraps_registered_tools(self) -> None:
        """Calling mcp.tool(...) after install must wrap the decorated function."""
        captured: list[str] = []

        class _Stub:
            def tool(self, *_args: object, **_kwargs: object) -> object:
                def decorator(func: object) -> object:
                    captured.append(getattr(func, "__name__", "?"))
                    return func

                return decorator

        stub = _Stub()
        install_tool_telemetry(stub)

        async def example() -> str:
            return "ok"

        decorator = stub.tool()  # type: ignore[no-untyped-call]
        decorator(example)
        # The wrapped function still carries the original name (functools.wraps),
        # but it is the wrapper that was registered.
        assert captured == ["example"]


class TestCaptureDoesNotRaiseWhenUnconfigured:
    @pytest.mark.anyio
    async def test_unconfigured_capture_is_no_op(self) -> None:
        # _CONFIGURED is False under unit tests (POSTHOG_API_KEY unset).
        # Just confirm the wrapped tool runs without exploding.
        @with_telemetry
        async def my_tool() -> str:
            return "ok"

        assert await my_tool() == "ok"


@pytest.fixture
def anyio_backend() -> Iterator[str]:
    yield "asyncio"
