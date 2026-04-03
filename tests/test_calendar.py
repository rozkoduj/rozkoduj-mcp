"""Tests for rozkoduj_mcp.tools.calendar."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.calendar import calendar


def _mock_result() -> dict:
    return {
        "count": 2,
        "events": [
            {"title": "Non-Farm Payrolls", "importance": 1},
            {"title": "CPI", "importance": 1},
        ],
    }


class TestCalendar:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.calendar.scanner")
    async def test_returns_events(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.calendar = AsyncMock(return_value=_mock_result())

        result = await calendar()

        mock_scanner.calendar.assert_called_once_with(days=7, countries="US", importance=0)
        assert result["count"] == 2

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.calendar.scanner")
    async def test_custom_params(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.calendar = AsyncMock(return_value=_mock_result())

        await calendar(days=14, countries="US,EU", importance=1)

        mock_scanner.calendar.assert_called_once_with(days=14, countries="US,EU", importance=1)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.calendar.scanner")
    async def test_clamps_days(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.calendar = AsyncMock(return_value=_mock_result())

        await calendar(days=999)

        mock_scanner.calendar.assert_called_once_with(days=30, countries="US", importance=0)
