"""MCP tool: the instrument catalog and per-symbol dossiers."""

from typing import Annotated, Any

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS

# Ticker charset - no wildcards, no separators; path-safe (the symbol lands
# in the upstream request path).
Symbol = Annotated[
    str, Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.^=-]+$")
]
# Catalog facet values are lowercase slugs (equity, crypto, live, ...).
Facet = Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[a-z_]+$")]


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def instrument(
    symbol: Symbol | None = None,
    asset_class: Facet | None = None,
    status: Facet | None = None,
    limit: Annotated[int, Field(ge=1, le=200)] = 50,
    offset: Annotated[int, Field(ge=0, le=10000)] = 0,
) -> dict[str, Any]:
    """The instrument catalog, or one instrument's dossier.

    Without `symbol`: the catalog of covered markets - name, venue, asset
    class, status - filterable by `asset_class` (`equity`, `crypto`,
    `index`, `commodity`) or `status`. Use for "which markets do you
    cover?", "list your crypto instruments".

    With `symbol`: the dossier - identity (name, venue, currency, sector)
    plus `stats`, the analytics summary: buy-and-hold facts (`cagr`,
    `ann_vol`, `max_dd`, `time_underwater_pct`) and the six-axis character
    fingerprint (`radar`, with `verdict`). `stats` is null for freshly added
    instruments. Case-insensitive: `AAPL` finds `AAPL.US`; a venue-suffixed
    id (`RY.TO`) pins one listing. Use for "what do you know about AAPL?",
    "how volatile is BTC?".

    For strategies backtested on the instrument, use `leaderboard` with the
    same symbol.
    """
    if symbol:
        return await scanner.instrument_details(symbol)
    return await scanner.list_instruments(
        asset_class=asset_class, status=status, limit=limit, offset=offset
    )
