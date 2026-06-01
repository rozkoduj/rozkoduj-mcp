"""Tests for rozkoduj_mcp.tools.decode."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.decode import decode


def _mock_decode_result() -> dict[str, Any]:
    return {
        "symbol": "AAPL",
        "technical": {"score": 72},
        "fundamental": {"score": 65},
        "sentiment": {"score": 58},
    }


class TestDecode:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.decode.scanner")
    async def test_basic_call(self, mock_scanner: MagicMock) -> None:
        mock_scanner.decode = AsyncMock(return_value=_mock_decode_result())

        result = await decode(symbol="AAPL")

        mock_scanner.decode.assert_called_once_with(symbol="AAPL", query="", lang="en")
        assert result["symbol"] == "AAPL"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.decode.scanner")
    async def test_with_query(self, mock_scanner: MagicMock) -> None:
        mock_scanner.decode = AsyncMock(return_value=_mock_decode_result())

        await decode(symbol="SHL.DE", query="Siemens Healthineers")

        mock_scanner.decode.assert_called_once_with(
            symbol="SHL.DE", query="Siemens Healthineers", lang="en"
        )

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.decode.scanner")
    async def test_with_lang(self, mock_scanner: MagicMock) -> None:
        mock_scanner.decode = AsyncMock(return_value=_mock_decode_result())

        await decode(symbol="ASML.AS", lang="de")

        mock_scanner.decode.assert_called_once_with(
            symbol="ASML.AS", query="", lang="de"
        )
