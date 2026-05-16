"""Tests for rozkoduj_mcp.tools.buzz."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.buzz import buzz


def _mock_result() -> dict:
    return {
        "query": "AAPL stock",
        "language": "en",
        "attention": "HIGH",
        "news": {"count": 47, "headlines": [{"title": "Apple news"}]},
        "wikipedia": {"available": True, "trend": "SPIKE", "spike_ratio": 2.54},
    }


class TestBuzz:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_returns_attention(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        result = await buzz("AAPL stock", lang="en")

        mock_scanner.buzz.assert_called_once_with(
            "AAPL stock", lang="en", wiki_article=None
        )
        assert result["attention"] == "HIGH"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_with_wiki(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        await buzz("AAPL", wiki_article="Apple_Inc")

        mock_scanner.buzz.assert_called_once_with(
            "AAPL", lang="en", wiki_article="Apple_Inc"
        )

    @pytest.mark.anyio
    async def test_rejects_long_query(self) -> None:
        with pytest.raises(ValueError, match="query"):
            await buzz("x" * 101)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_has_news_and_wiki(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        result = await buzz("AAPL")

        assert "news" in result
        assert "wikipedia" in result
