"""MCP server instance for rozkoduj-mcp."""

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "rozkoduj",
    instructions=(
        "Market screening and technical analysis for stocks, crypto, and forex. "
        "Use 'scan' to screen markets, 'analyze' for single-symbol TA, "
        "'movers' for top gainers/losers, 'compare' for multi-symbol comparison, "
        "'multitf' for multi-timeframe analysis."
    ),
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8080")),
    stateless_http=True,
    json_response=True,
)

# Import tool modules so @mcp.tool() decorators register with the server.
import rozkoduj_mcp.tools.analyze as _analyze  # noqa: F401, E402
import rozkoduj_mcp.tools.compare as _compare  # noqa: F401, E402
import rozkoduj_mcp.tools.movers as _movers  # noqa: F401, E402
import rozkoduj_mcp.tools.multitf as _multitf  # noqa: F401, E402
import rozkoduj_mcp.tools.scan as _scan  # noqa: F401, E402
