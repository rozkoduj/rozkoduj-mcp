"""MCP tool: the strategy leaderboard."""

from typing import Annotated, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Symbol
from rozkoduj_mcp.tools.models import StrategyPage

# Family slugs mirror the API bound exactly - anything looser 422s upstream.
FamilySlug = Annotated[str, Field(max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


@mcp.tool(title="Strategy leaderboard", annotations=TOOL_ANNOTATIONS)
async def leaderboard(
    status: Literal["active", "archived", "all"] = "active",
    sort: Literal["score_desc", "apy_desc", "recent"] = "score_desc",
    family: FamilySlug | None = None,
    symbol: Symbol | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
    offset: Annotated[int, Field(ge=0, le=10000)] = 0,
) -> StrategyPage:
    """The strategy leaderboard - published, backtested strategies, ranked.

    Use for "what are the best strategies?", "what works best on AAPL?".
    `symbol` narrows to strategies backtested on one instrument and makes
    `best_run` the best run *on that instrument* - case-insensitive, plain
    tickers just work (`aapl` finds `aapl-us`, `btc` finds `btc-usd`; the
    full slug like `ry-ca` pins one listing when a ticker trades in several
    markets).

    There is NO risk filter here: `unit_risk_band` is returned on `best_run`
    but cannot be filtered or sorted on. Answer "best aggressive strategy?"
    by fetching a page and reading `unit_risk_band`, never by inventing a
    parameter.

    Sorting: `score_desc` (default) ranks by the Rozkoduj Score - the
    headline leaderboard axis; `apy_desc` ranks by annualised return in USD
    (`cagr_usd` - the cross-market canon, immune to weak-currency inflation;
    local `cagr` is the fallback); `recent` is newest first.

    Each item carries `algorithm_uid` (ULID), `slug`, i18n
    `name`/`description`, `family`/`variant`, and `best_run` with hot
    metrics: `symbol` (the instrument the metrics were earned on), `cagr`
    (APY in the instrument's local currency), `cagr_usd` (APY in USD - use
    this whenever comparing across markets), `max_drawdown`, `win_rate`,
    `num_trades`, `rozkoduj_score`, `rozkoduj_band`, the risk mode
    (`unit_risk_band`, `unit_risk_score`), and a `sparkline`.

    For one strategy's full dossier use `strategy`.
    """
    return StrategyPage(
        **await scanner.list_strategies(
            status=status,
            sort=sort,
            family=family,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )
    )
