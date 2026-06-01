"""Contract tests: tool input schemas carry the declarative length bounds.

These replace the old imperative `validate_str` unit tests. With Pydantic
`Field` constraints the bound lives in the generated JSON Schema (so the
calling LLM sees it and self-limits) and FastMCP/Pydantic enforce it before
the tool body runs - so we assert the published contract, not a hand-rolled
raise inside each tool.
"""

from typing import Any

import pytest

from rozkoduj_mcp.server import mcp


async def _schemas() -> dict[str, dict[str, Any]]:
    return {tool.name: tool.inputSchema for tool in await mcp.list_tools()}


class TestToolParameterBounds:
    @pytest.mark.anyio
    async def test_search_queries_allow_2_to_300_chars(self) -> None:
        schemas = await _schemas()
        for tool in ("search_articles", "search_knowledge"):
            query = schemas[tool]["properties"]["query"]
            assert query["minLength"] == 2
            assert query["maxLength"] == 300

    @pytest.mark.anyio
    async def test_short_string_params_capped_at_100(self) -> None:
        schemas = await _schemas()
        for tool, param in (
            ("analyze", "symbol"),
            ("score", "symbol"),
            ("fundamentals", "symbol"),
            ("strategy_details", "identifier"),
            ("calendar", "countries"),
            ("scan", "sort_by"),
            ("decode", "symbol"),
            ("multitf", "symbol"),
            ("buzz", "query"),
        ):
            assert schemas[tool]["properties"][param]["maxLength"] == 100

    @pytest.mark.anyio
    async def test_language_codes_bounded_2_to_10(self) -> None:
        # lang / locale are short ISO 639-1 codes, not free text - they carry a
        # tighter bound than the generic ShortStr params above.
        schemas = await _schemas()
        for tool, param in (("decode", "lang"), ("buzz", "lang")):
            field = schemas[tool]["properties"][param]
            assert field["minLength"] == 2
            assert field["maxLength"] == 10
        # search_articles.locale is `str | None` - bound on the string variant.
        locale = schemas["search_articles"]["properties"]["locale"]
        string_variant = next(v for v in locale["anyOf"] if v.get("type") == "string")
        assert string_variant["minLength"] == 2
        assert string_variant["maxLength"] == 10

    @pytest.mark.anyio
    async def test_compare_symbols_capped_per_item(self) -> None:
        schemas = await _schemas()
        items = schemas["compare"]["properties"]["symbols"]["items"]
        assert items["maxLength"] == 100

    @pytest.mark.anyio
    async def test_optional_param_still_bounded(self) -> None:
        # list_strategies.family is `str | None` but still capped when present.
        schemas = await _schemas()
        family = schemas["list_strategies"]["properties"]["family"]
        string_variant = next(v for v in family["anyOf"] if v.get("type") == "string")
        assert string_variant["maxLength"] == 100


class TestBoundsEnforcedEndToEnd:
    """Schema assertions prove the bound is advertised; these prove FastMCP
    actually rejects out-of-bounds input before the tool body runs."""

    @pytest.mark.anyio
    async def test_overlong_symbol_rejected(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="at most 100 characters"):
            await mcp.call_tool("analyze", {"symbol": "x" * 101})

    @pytest.mark.anyio
    async def test_too_short_query_rejected(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="at least 2 characters"):
            await mcp.call_tool("search_articles", {"query": "x"})

    @pytest.mark.anyio
    async def test_overlong_lang_rejected(self) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="at most 10 characters"):
            await mcp.call_tool("buzz", {"query": "AAPL", "lang": "x" * 11})
