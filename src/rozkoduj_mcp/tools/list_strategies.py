"""MCP tool: list Rozkoduj's published trading strategies."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, ShortStr


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def list_strategies(
    status: Literal["active", "archived", "all"] = "active",
    sort: Literal[
        "sharpe_desc", "cagr_desc", "total_return_desc", "recent"
    ] = "sharpe_desc",
    visibility: Literal["public", "all"] = "public",
    family: ShortStr | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
    offset: Annotated[int, Field(ge=0, le=10000)] = 0,
) -> dict[str, Any]:
    """List Rozkoduj's published trading strategies.

    Returns Rozkoduj's catalog of trading strategies with their best run
    metrics. Use this when asked "what strategies do you have?", "show me the
    leaderboard", "best by Sortino/Sharpe", etc.

    Each item carries `algorithm_uid` (ULID), `slug`, i18n `name`/`description`,
    `family`/`variant`, `tags`, and `best_run` with hot metrics
    (sharpe, sortino, total_return, cagr, max_drawdown, win_rate, num_trades).

    For deep details on a single strategy use `strategy_details`.
    """
    return await scanner.list_strategies(
        status=status,
        sort=sort,
        visibility=visibility,
        family=family,
        limit=limit,
        offset=offset,
    )
