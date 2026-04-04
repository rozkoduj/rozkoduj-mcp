# Rozkoduj MCP - Decode the Markets

[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=rozkoduj&config=eyJuYW1lIjoicm96a29kdWoiLCJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vbWNwLnJvemtvZHVqLmNvbS9tY3AifQ==)
[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=rozkoduj&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A//mcp.rozkoduj.com/mcp%22%7D)
[![CI](https://github.com/rozkoduj/rozkoduj-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rozkoduj/rozkoduj-mcp/actions)
[![PyPI](https://img.shields.io/pypi/v/rozkoduj-mcp?style=flat-square)](https://pypi.org/project/rozkoduj-mcp/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Decode the markets with screening, analysis, and scoring across stocks, crypto, and forex. Zero setup.

## Why Rozkoduj?

- **One URL, zero config** - no cloning, no local dependencies. Add the URL and go.
- **Global coverage** - US, EU, Asia, crypto, forex. Not just S&P 500.
- **Deep screening** - any indicator, fundamental, or performance metric as a filter.
- **TA + fundamentals combined** - smart screens that mix technical signals with valuation data.
- **Market regime detection** - CNN Fear & Greed, crypto Fear & Greed, VIX in one call.
- **Per-ticker attention signal** - news headlines + Wikipedia pageview spike detection globally.
- **MCP Resources & Prompts** - proper spec-compliant context and workflow templates.

## Installation

Connect to the hosted MCP server:

```
https://mcp.rozkoduj.com/mcp
```

Works immediately with any MCP client.

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
claude mcp add --transport http rozkoduj https://mcp.rozkoduj.com/mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Add to your config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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
<summary><b>Windsurf</b></summary>

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "rozkoduj": {
      "serverUrl": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>Gemini CLI</b></summary>

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "rozkoduj": {
      "httpUrl": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>Other Clients</b></summary>

For clients that support remote MCP:

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

## Available Tools

### Market Screening

| Tool | Description |
| ---- | ----------- |
| `scan` | Screen global markets by any indicator, fundamental, volume, market cap, and more. Flexible filtering and sorting. |
| `smart_screen` | Pre-built intelligent screens. Presets: `unusual_volume`, `oversold_bounce`, `breakout`, `momentum`, `dividend`, `value`, `growth`. Value and growth combine TA with fundamental data. |
| `movers` | Top gainers and losers across any market. Supports crypto, stocks, forex. |

### Analysis

| Tool | Description |
| ---- | ----------- |
| `score` | Holistic 0-100 score combining technical rating (40%), momentum (25%), volume quality (15%), and trend strength (20%). Returns a single actionable number with breakdown. |
| `analyze` | Single-symbol technical analysis: composite BUY/SELL/NEUTRAL rating + RSI, MACD, Bollinger Bands, ADX, and 30+ indicators across any timeframe. |
| `fundamentals` | Valuation (P/E, P/B, EV/EBITDA), quality scores (Piotroski F-Score, Altman Z-Score), analyst consensus (buy/hold/sell counts, 12-month price targets), upcoming earnings date with EPS forecast, and dividend data. |
| `compare` | Side-by-side technical analysis for up to 10 symbols at once. |
| `multitf` | Multi-timeframe analysis with alignment scoring. Default: 15m, 1h, 4h, 1d, 1W. |

### Market Intelligence

| Tool | Description |
| ---- | ----------- |
| `market_pulse` | Market regime detection: CNN Fear & Greed (US stocks, 7 sub-indicators), Alternative.me Fear & Greed (crypto), and VIX. Returns RISK-ON, RISK-OFF, or NEUTRAL verdict. |
| `buzz` | Per-ticker attention signal using Google News headline count and Wikipedia pageview trends. Detects spikes in public interest. Works globally in any language. |
| `calendar` | Economic calendar with upcoming macro events. Filter by days ahead, countries, and importance level. Shows actual vs forecast vs previous values. |

### Resources

Context data the AI can read to build better queries:

| Resource | Description |
| -------- | ----------- |
| `rozkoduj://markets` | Available markets (america, crypto, forex, poland, ...) |
| `rozkoduj://fields` | Popular screening fields with categories (technical, fundamental, performance) |
| `rozkoduj://operators` | Filter operators for scan (greater, less, in_range, crosses_above, ...) |

### Prompts

Pre-built workflows you can trigger as slash commands:

| Prompt | Description |
| ------ | ----------- |
| `morning_briefing` | Daily overview: market regime, top movers, economic calendar |
| `deep_dive(symbol)` | Full analysis: score + technicals + fundamentals + buzz + multi-timeframe |
| `find_opportunities(market)` | Scan for opportunities across multiple smart screens |

## Example Prompts

**Quick analysis:**
```
Score AAPL - should I buy?
What's the Piotroski F-Score for NVDA? Show me analyst price targets.
Multi-timeframe analysis for ETHUSDT - is it aligned bullish?
Compare AAPL, MSFT, GOOGL technical indicators.
```

**Market overview:**
```
What's the current market regime? Risk-on or risk-off?
What economic events are happening this week?
Check the buzz around CD Projekt (wiki_article: CD_Projekt).
```

**Smart screens:**
```
Find unusual volume stocks in the US market right now.
Show me oversold bounce candidates in crypto.
Find value stocks - low P/E with high Piotroski score.
Screen for growth stocks with strong earnings and momentum.
Show me high-dividend stocks with sustainable payout ratios.
```

**Custom screening:**
```
Screen US stocks with market cap above 10B sorted by change.
Find crypto with RSI below 30 and MACD crossing above signal.
```

## Data

Market data via [rozkoduj](https://rozkoduj.com) data API.

Auto-detects exchanges: `BTCUSDT` resolves to Binance, `AAPL` to NASDAQ, `EURUSD` to Forex.

## Self-Hosting

```bash
# Install from PyPI
pip install rozkoduj-mcp

# Or run directly with uvx
uvx rozkoduj-mcp

# Docker
docker build -t rozkoduj-mcp .
docker run -p 8080:8080 rozkoduj-mcp

# Remote mode (streamable-http)
MCP_TRANSPORT=streamable-http PORT=8080 uvx rozkoduj-mcp
```

## License

MIT - [rozkoduj.com](https://rozkoduj.com)
