"""MCP tool: one strategy's full dossier."""

from typing import Annotated, Any

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS

# Slug / ULID characters only. The identifier is interpolated into the
# upstream request path, so the pattern also keeps it path-safe.
StrategyId = Annotated[str, Field(max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def strategy(identifier: StrategyId) -> dict[str, Any]:
    """One strategy's full dossier, including its backtest summary.

    `identifier` is either the URL slug (e.g. `ma-crossover`) or the
    `algorithm_uid` (ULID, e.g. `01J7...`). Returns i18n names/descriptions,
    family/variant/version metadata and the `best_run` backtest summary:
    `rozkoduj_score`/`rozkoduj_band` (ranking axis), `cagr` (APY in the
    instrument's local currency), `cagr_usd` (APY in USD - the cross-market
    canon), `max_drawdown`, `win_rate`, `num_trades`, the risk mode
    (`risk_character`, `character_score`), plus `sparkline`, `params_public`,
    and `data_start`/`data_end`.

    Use this after `leaderboard` once a candidate is chosen, or when the
    user names a strategy directly. Raises a not-found error when no
    strategy matches `identifier`.
    """
    return await scanner.strategy_details(identifier)
