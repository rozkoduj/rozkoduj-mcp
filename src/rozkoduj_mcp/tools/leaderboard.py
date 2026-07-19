"""MCP tool: the strategy leaderboard."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS

# Ticker charset: dots, carets, dashes and equals cover BRK.B-style symbols
# plus index/FX notations. No wildcards, no separators.
Symbol = Annotated[
    str, Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.^=-]+$")
]
# Family slugs mirror the API bound exactly - anything looser 422s upstream.
FamilySlug = Annotated[str, Field(max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def leaderboard(
    status: Literal["active", "archived", "all"] = "active",
    sort: Literal["score_desc", "apy_desc", "recent"] = "score_desc",
    visibility: Literal["public", "all"] = "public",
    family: FamilySlug | None = None,
    symbol: Symbol | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
    offset: Annotated[int, Field(ge=0, le=10000)] = 0,
) -> dict[str, Any]:
    """The strategy leaderboard - published, backtested strategies, ranked.

    Use for "what are the best strategies?", "what works best on AAPL?",
    "best aggressive strategy?". `symbol` narrows to strategies backtested on
    one instrument and makes `best_run` the best run *on that instrument* -
    case-insensitive, plain tickers just work (`AAPL` finds `AAPL.US`, `btc`
    finds `BTCUSDT`, a venue-suffixed symbol like `RY.TO` pins one listing).

    Sorting: `score_desc` (default) ranks by the Rozkoduj Score - the
    headline leaderboard axis; `apy_desc` ranks by annualised return in USD
    (`cagr_usd` - the cross-market canon, immune to weak-currency inflation;
    local `cagr` is the fallback); `recent` is newest first.

    Each item carries `algorithm_uid` (ULID), `slug`, i18n
    `name`/`description`, `family`/`variant`, and `best_run` with hot
    metrics: `symbol` (the instrument the metrics were earned on), `cagr`
    (APY in the instrument's local currency), `cagr_usd` (APY in USD - use
    this whenever comparing across markets), `max_drawdown`, `win_rate`,
    `num_trades`, `rozkoduj_score`, `rozkoduj_band`, and the risk mode
    (`risk_character`, `character_score`).

    For one strategy's full dossier use `strategy`.
    """
    return await scanner.list_strategies(
        status=status,
        sort=sort,
        visibility=visibility,
        family=family,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )
