# Rozkoduj MCP - Decode the Markets

[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=rozkoduj&config=eyJuYW1lIjoicm96a29kdWoiLCJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vbWNwLnJvemtvZHVqLmNvbS9tY3AifQ==)
[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=rozkoduj&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A//mcp.rozkoduj.com/mcp%22%7D)
[![CI](https://github.com/rozkoduj/rozkoduj-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rozkoduj/rozkoduj-mcp/actions)
[![PyPI](https://img.shields.io/pypi/v/rozkoduj-mcp?style=flat-square)](https://pypi.org/project/rozkoduj-mcp/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue?style=flat-square)](https://python.org)
[![Coverage](https://img.shields.io/codecov/c/github/rozkoduj/rozkoduj-mcp?style=flat-square)](https://codecov.io/gh/rozkoduj/rozkoduj-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Decode the markets with your AI assistant. Screening, analysis, and scoring across stocks, crypto, and forex.

### Just ask:

```
"Score AAPL - should I buy?"
"What are today's hidden gems in crypto?"
"Full analysis of NVDA - technicals, fundamentals, and news"
"Is the market risk-on or risk-off right now?"
```

## What You Get

- **Ask "should I buy?" and get a real answer** - every symbol gets a 0-100 score combining technical signals, fundamental health, and news sentiment into a single BUY/HOLD/SELL verdict
- **See what the market is hiding** - anomaly radar scans 20+ global markets and surfaces unusual activity (volume spikes, extreme readings, big moves) ranked by 1-5 star surprise score
- **Check if timeframes agree** - daily, 4h, and weekly signals shown side by side so you know if a trend is confirmed or conflicting
- **Screen any market your way** - filter by 30+ indicators, fundamentals, or performance metrics. Or use preset screens: unusual volume, oversold bounce, breakout, value, momentum, dividend, growth
- **Know the market mood** - fear & greed indices, VIX, and economic calendar in one call
- **Catch the buzz** - news attention signal for any ticker in any language

## Quick Start

Add the hosted server URL to your MCP client:

```
https://mcp.rozkoduj.com/mcp
```

No API key. No setup. Works immediately.

<details>
<summary><b>Cursor</b></summary>

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "rozkoduj": {
      "url": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>VS Code</b></summary>

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "rozkoduj": {
      "type": "http",
      "url": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add rozkoduj --transport http https://mcp.rozkoduj.com/mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rozkoduj": {
      "type": "http",
      "url": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>Self-hosted (PyPI / Docker)</b></summary>

```bash
pip install rozkoduj-mcp       # from PyPI
uvx rozkoduj-mcp               # or run directly
docker run -p 8080:8080 $(docker build -q .)  # Docker
```
</details>

## Tools

### Find opportunities

| Tool | What it does |
| ---- | ------------ |
| `digest` | Scans all global markets and surfaces anomalies ranked by 1-5 star surprise score. Volume spikes, RSI extremes, big moves, 52-week highs/lows - with fundamental context for each gem. |
| `scan` | Custom screening with any combination of filters, columns, and sorting. 30+ indicators and fundamental metrics. |
| `smart_screen` | One-word preset screens: `unusual_volume`, `oversold_bounce`, `breakout`, `momentum`, `value`, `dividend`, `growth`. |
| `movers` | Top gainers and losers with quality filters. |

### Analyze a symbol

| Tool | What it does |
| ---- | ------------ |
| `decode` | Full 3-dimensional analysis: technical (daily, 4h, weekly), fundamental (valuation, analysts, earnings), and news sentiment. Each dimension scored 0-100, combined into a single verdict. |
| `score` | Quick 0-100 score combining technical rating, momentum, volume quality, and trend strength. |
| `analyze` | Detailed technical analysis: RSI, MACD, Bollinger Bands, ADX, and 30+ indicators on any timeframe. |
| `fundamentals` | Valuation (P/E, P/B, EV/EBITDA), quality scores (Piotroski, Altman Z), analyst consensus, earnings dates, dividends. |
| `compare` | Side-by-side technical analysis for up to 10 symbols. |
| `multitf` | Multi-timeframe alignment scoring across 15m, 1h, 4h, 1d, 1W. |

### Read the market

| Tool | What it does |
| ---- | ------------ |
| `market_pulse` | Market regime: fear & greed indices + VIX = RISK-ON, RISK-OFF, or NEUTRAL. |
| `buzz` | News attention signal for any ticker in any language. |
| `calendar` | Upcoming economic events with actual vs forecast vs previous. |

<details>
<summary><b>Resources & Prompts</b></summary>

| Type | Name | Description |
| ---- | ---- | ----------- |
| Resource | `rozkoduj://markets` | Available markets with IDs |
| Resource | `rozkoduj://fields` | Screening fields by category |
| Resource | `rozkoduj://operators` | Filter operators for scan |
| Prompt | `morning_briefing` | Daily overview: regime, movers, calendar |
| Prompt | `deep_dive(symbol)` | Full analysis: all tools combined |
| Prompt | `find_opportunities(market)` | Multi-screen opportunity scan |

</details>

## Example Prompts

**"Should I buy?"**
```
Score AAPL - should I buy?
Decode NVDA - full 3D analysis with news
Compare AAPL, MSFT, GOOGL - which one looks best?
```

**"What's interesting today?"**
```
What are today's market anomalies? Any hidden gems?
Find unusual volume stocks in crypto.
Show me oversold bounce candidates in European markets.
```

**"What's going on?"**
```
Is the market risk-on or risk-off right now?
What economic events are happening this week?
Is there any buzz around Tesla?
```

## Coverage

20+ markets worldwide. Symbols are auto-detected - `BTCUSDT` routes to crypto, `AAPL` to US stocks, `EURUSD` to forex.


## License

MIT - [rozkoduj.com](https://rozkoduj.com)
