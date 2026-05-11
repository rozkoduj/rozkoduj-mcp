"""Tests for rozkoduj_mcp.tools.search_knowledge."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.search_knowledge import search_knowledge


def _mock_result() -> dict[str, Any]:
    return {
        "query": "risk",
        "items": [
            {
                "doc_id": "lessons/risk-101",
                "chunk_index": 0,
                "title": "Risk Lessons 101",
                "chunk_text": "Position sizing matters more than entry timing.",
                "parent_text": None,
                "context_prefix": None,
            }
        ],
    }


class TestSearchKnowledge:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_knowledge.scanner")
    async def test_returns_results(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_knowledge = AsyncMock(return_value=_mock_result())

        result = await search_knowledge(query="risk", limit=3)

        mock_scanner.search_knowledge.assert_called_once_with(query="risk", limit=3)
        assert result == _mock_result()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_knowledge.scanner")
    async def test_default_limit_is_five(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_knowledge = AsyncMock(return_value={"query": "q", "items": []})

        await search_knowledge(query="anything")

        assert mock_scanner.search_knowledge.call_args.kwargs["limit"] == 5

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_knowledge.scanner")
    async def test_limit_clamped(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_knowledge = AsyncMock(return_value={"query": "q", "items": []})

        await search_knowledge(query="q", limit=99)

        assert mock_scanner.search_knowledge.call_args.kwargs["limit"] == 20
