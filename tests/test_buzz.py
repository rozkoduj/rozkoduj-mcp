"""Tests for rozkoduj_mcp.tools.buzz."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.buzz import buzz


def _mock_result() -> dict:
    return {
        "query": "JSW akcje",
        "language": "pl",
        "attention": "HIGH",
        "news": {"count": 47, "headlines": [{"title": "JSW news"}]},
        "wikipedia": {"available": True, "trend": "SPIKE", "spike_ratio": 2.54},
    }


class TestBuzz:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_returns_attention(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        result = await buzz("JSW akcje", lang="pl")

        mock_scanner.buzz.assert_called_once_with("JSW akcje", lang="pl", wiki_article=None)
        assert result["attention"] == "HIGH"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_with_wiki(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        await buzz("JSW", wiki_article="Jastrzebska_Spolka_Weglowa")

        mock_scanner.buzz.assert_called_once_with(
            "JSW", lang="en", wiki_article="Jastrzebska_Spolka_Weglowa"
        )

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.buzz.scanner")
    async def test_has_news_and_wiki(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.buzz = AsyncMock(return_value=_mock_result())

        result = await buzz("JSW")

        assert "news" in result
        assert "wikipedia" in result
