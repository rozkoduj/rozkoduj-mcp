"""MCP prompts: user-controlled workflow templates."""

from mcp.server.fastmcp.prompts.base import Message

from rozkoduj_mcp.server import mcp


@mcp.prompt()
def morning_briefing() -> list[Message]:
    """Daily market overview - regime, movers, and upcoming events."""
    return [
        Message(
            role="user",
            content=(
                "Give me a morning market briefing. Use these tools in order:\n"
                "1. market_pulse - current regime (risk-on/off)\n"
                "2. movers(market='crypto', direction='both', limit=5) - top crypto movers\n"
                "3. movers(market='us', direction='both', limit=5) - top US stock movers\n"
                "4. calendar(days=1, importance=1) - high-importance events today\n\n"
                "Summarize the overall market tone and highlight anything unusual."
            ),
        ),
    ]


@mcp.prompt()
def deep_dive(symbol: str) -> list[Message]:
    """Full analysis of a single symbol - score, technicals, fundamentals, buzz."""
    return [
        Message(
            role="user",
            content=(
                f"Do a deep dive analysis of {symbol}. Use these tools:\n"
                f"1. score(symbol='{symbol}') - holistic 0-100 score\n"
                f"2. analyze(symbol='{symbol}') - technical analysis\n"
                f"3. fundamentals(symbol='{symbol}') - valuation and earnings\n"
                f"4. buzz(query='{symbol}') - news attention signal\n"
                f"5. multitf(symbol='{symbol}') - multi-timeframe alignment\n\n"
                "Synthesize all data into a clear buy/hold/sell assessment with key "
                "reasons. Flag any conflicting signals between timeframes or between "
                "technicals and fundamentals."
            ),
        ),
    ]


@mcp.prompt()
def find_opportunities(market: str = "us") -> list[Message]:
    """Scan for trading opportunities using smart screens and buzz."""
    return [
        Message(
            role="user",
            content=(
                f"Find trading opportunities in the {market} market. Run these screens:\n"
                f"1. smart_screen(preset='unusual_volume', market='{market}', limit=10)\n"
                f"2. smart_screen(preset='oversold_bounce', market='{market}', limit=10)\n"
                f"3. smart_screen(preset='breakout', market='{market}', limit=10)\n"
                f"4. smart_screen(preset='value', market='{market}', limit=10)\n\n"
                "For the top 3 most interesting results across all screens, run "
                "score() to get a holistic rating.\n\n"
                "Present a ranked list of opportunities with the reasoning for each."
            ),
        ),
    ]
