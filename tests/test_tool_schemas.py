"""Contract tests: tool input schemas carry the declarative length bounds.

With Pydantic `Field` constraints the bound lives in the generated JSON Schema
(so the calling LLM sees it and self-limits) and the server/Pydantic enforce it
before the tool body runs - so we assert the published contract, not a
hand-rolled raise inside each tool.
"""

from typing import Any

import pytest

from rozkoduj_mcp.server import mcp


async def _schemas() -> dict[str, dict[str, Any]]:
    return {tool.name: tool.input_schema for tool in await mcp.list_tools()}


def _string_variant(prop: dict[str, Any]) -> dict[str, Any]:
    """The string arm of a `str | None` property schema."""
    return next(v for v in prop["anyOf"] if v.get("type") == "string")


class TestToolSurface:
    @pytest.mark.anyio
    async def test_surface_mirrors_the_site_pillars(self) -> None:
        # One tool per pillar: the leaderboard, a strategy dossier, the
        # instrument catalog/dossier, and the research search. Guards against
        # a tool being added without an explicit decision.
        names = set((await _schemas()).keys())
        assert names == {"leaderboard", "strategy", "instrument", "research"}


class TestToolParameterBounds:
    @pytest.mark.anyio
    async def test_research_query_allows_2_to_300_chars(self) -> None:
        schemas = await _schemas()
        query = schemas["research"]["properties"]["query"]
        assert query["minLength"] == 2
        assert query["maxLength"] == 300

    @pytest.mark.anyio
    async def test_research_locale_is_the_supported_enum(self) -> None:
        # The api pins locale to en/pl - a looser schema here would surface
        # as a fake backend outage when the api 422s the value.
        schemas = await _schemas()
        locale = schemas["research"]["properties"]["locale"]
        variant = _string_variant(locale)
        assert variant["enum"] == ["en", "pl"]

    @pytest.mark.anyio
    async def test_leaderboard_family_mirrors_the_api_bound(self) -> None:
        schemas = await _schemas()
        family = schemas["leaderboard"]["properties"]["family"]
        variant = _string_variant(family)
        assert variant["maxLength"] == 64
        assert variant["pattern"] == "^[A-Za-z0-9_-]+$"

    @pytest.mark.anyio
    async def test_symbols_are_ticker_safe(self) -> None:
        # Symbols reach the upstream query (leaderboard) and the request
        # path (instrument) - the schema pins them to ticker characters.
        schemas = await _schemas()
        for tool in ("leaderboard", "instrument"):
            variant = _string_variant(schemas[tool]["properties"]["symbol"])
            assert variant["minLength"] == 1, tool
            assert variant["maxLength"] == 20, tool
            # First char alphanumeric/caret: a symbol can never be a pure
            # dot sequence, so it can never collapse the upstream path.
            assert variant["pattern"] == "^[A-Za-z0-9^][A-Za-z0-9.^=-]*$", tool

    @pytest.mark.anyio
    async def test_instrument_facets_are_slug_safe(self) -> None:
        schemas = await _schemas()
        for param in ("asset_class", "status"):
            variant = _string_variant(schemas["instrument"]["properties"][param])
            assert variant["pattern"] == "^[a-z_]+$", param
            assert variant["maxLength"] == 32, param

    @pytest.mark.anyio
    async def test_numeric_params_carry_min_and_max(self) -> None:
        # Numeric bounds live in the schema (not a silent clamp in the tool
        # body) so the calling LLM sees the range and self-limits.
        schemas = await _schemas()
        for tool, param, low, high in (
            ("leaderboard", "limit", 1, 50),
            ("instrument", "limit", 1, 200),
            ("research", "limit", 1, 20),
        ):
            field = schemas[tool]["properties"][param]
            assert field["minimum"] == low, f"{tool}.{param}"
            assert field["maximum"] == high, f"{tool}.{param}"

    @pytest.mark.anyio
    async def test_strategy_identifier_is_path_safe(self) -> None:
        # The identifier lands in the upstream request path, so the schema
        # restricts it to slug / ULID characters - no separators or dots.
        schemas = await _schemas()
        identifier = schemas["strategy"]["properties"]["identifier"]
        assert identifier["pattern"] == "^[A-Za-z0-9_-]+$"
        assert identifier["maxLength"] == 100

    @pytest.mark.anyio
    async def test_pagination_offset_bounded(self) -> None:
        schemas = await _schemas()
        for tool in ("leaderboard", "instrument"):
            offset = schemas[tool]["properties"]["offset"]
            assert offset["minimum"] == 0, tool
            assert offset["maximum"] == 10000, tool


class TestBoundsEnforcedEndToEnd:
    """Schema assertions prove the bound is advertised; these prove the server
    actually rejects out-of-bounds input before the tool body runs."""

    @pytest.mark.anyio
    async def test_too_short_query_rejected(self) -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="at least 2 characters"):
            await mcp.call_tool("research", {"query": "x"})

    @pytest.mark.anyio
    async def test_overlong_query_rejected(self) -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="at most 300 characters"):
            await mcp.call_tool("research", {"query": "x" * 301})

    @pytest.mark.anyio
    async def test_oversized_limit_rejected(self) -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="less than or equal to 50"):
            await mcp.call_tool("leaderboard", {"limit": 200})

    @pytest.mark.anyio
    async def test_negative_offset_rejected(self) -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="greater than or equal to 0"):
            await mcp.call_tool("leaderboard", {"offset": -5})

    @pytest.mark.anyio
    async def test_path_like_identifier_rejected(self) -> None:
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="match pattern"):
            await mcp.call_tool("strategy", {"identifier": "../strategies"})

    @pytest.mark.anyio
    async def test_wildcard_symbol_rejected(self) -> None:
        # % would turn the upstream case-insensitive match into a wildcard.
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="match pattern"):
            await mcp.call_tool("leaderboard", {"symbol": "A%"})

    @pytest.mark.anyio
    async def test_path_like_instrument_symbol_rejected(self) -> None:
        # The instrument symbol lands in the request path - separators out.
        from mcp.server.mcpserver.exceptions import ToolError

        with pytest.raises(ToolError, match="match pattern"):
            await mcp.call_tool("instrument", {"symbol": "../admin"})

    @pytest.mark.anyio
    async def test_dot_segment_symbols_rejected(self) -> None:
        # "." and ".." are RFC 3986 dot-segments: httpx2 would collapse
        # /instruments/.. to the API root instead of a dossier path.
        from mcp.server.mcpserver.exceptions import ToolError

        for symbol in (".", ".."):
            with pytest.raises(ToolError, match="match pattern"):
                await mcp.call_tool("instrument", {"symbol": symbol})


class TestToolOutputSchemas:
    """The output side of the same contract.

    Every tool used to return `dict[str, Any]`, which the SDK renders as a bare
    object schema: the ~40 field names the docstrings promise existed nowhere a
    client could read them, and a renamed field just vanished from the response
    instead of failing. These assert the schema is published AND that it is
    specific enough to be worth publishing.
    """

    @pytest.mark.anyio
    async def test_every_tool_publishes_a_specific_output_schema(self) -> None:
        for tool in await mcp.list_tools():
            schema = tool.output_schema
            assert schema is not None, f"{tool.name} publishes no output schema"
            props = schema.get("properties") or {}
            assert props, f"{tool.name} publishes an output schema with no fields"

    @pytest.mark.anyio
    async def test_no_tool_output_is_wrapped_in_result(self) -> None:
        # Scalars, lists, tuples and unions get wrapped by the SDK into
        # {"result": ...}. Every tool here returns a model precisely so the
        # payload stays where existing clients already read it - a wrapper
        # appearing means someone changed a return type to a union.
        for tool in await mcp.list_tools():
            props = (tool.output_schema or {}).get("properties") or {}
            assert set(props) != {"result"}, (
                f"{tool.name} output got wrapped in a result envelope"
            )

    @pytest.mark.anyio
    async def test_documented_fields_are_in_the_schema(self) -> None:
        # A sample per tool, chosen from what the docstring tells the model to
        # look for. If a field is renamed upstream, this fails here rather than
        # silently shrinking the response.
        expected = {
            "leaderboard": {"items", "total", "limit", "offset"},
            "strategy": {"algorithm_uid", "slug", "name", "best_run"},
            "research": {"query", "articles", "knowledge", "locked"},
            "instrument": {"items", "listing_slug", "stats", "asset_class"},
        }
        by_name = {tool.name: tool for tool in await mcp.list_tools()}
        for name, fields in expected.items():
            props = set((by_name[name].output_schema or {}).get("properties") or {})
            assert fields <= props, f"{name} is missing {fields - props}"
