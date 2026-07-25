"""Tests for rozkoduj_mcp.server lifespan."""

import pytest

from rozkoduj_mcp.server import app_lifespan, mcp
from rozkoduj_mcp.services import scanner


class TestAppLifespan:
    @pytest.mark.anyio
    async def test_creates_and_closes_client(self) -> None:
        assert scanner.client is None

        async with app_lifespan(mcp):
            assert scanner.client is not None

        # mypy narrows the module global to non-None above and cannot model the
        # lifespan resetting it on exit, so it reads this line as unreachable.
        # The assertion is the point of the test: teardown must clear the client.
        assert scanner.client is None  # type: ignore[unreachable]
