"""rozkoduj-mcp: MCP server for market screening and technical analysis."""

import os
from importlib.metadata import version

__version__ = version("rozkoduj-mcp")


def main() -> None:
    """Entry point for the MCP server."""
    from rozkoduj_mcp.server import mcp

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)  # type: ignore[arg-type]
