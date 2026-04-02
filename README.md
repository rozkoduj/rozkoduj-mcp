# Rozkoduj MCP Server

[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=rozkoduj&config=eyJuYW1lIjoicm96a29kdWoiLCJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vbWNwLnJvemtvZHVqLmNvbS9tY3AifQ==)
[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=rozkoduj&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A//mcp.rozkoduj.com/mcp%22%7D)
[![CI](https://github.com/rozkoduj/rozkoduj-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rozkoduj/rozkoduj-mcp/actions)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Real-time market intelligence for AI assistants. Screen 3000+ fields across stocks, crypto, forex. Technical analysis with BUY/SELL ratings. No API key needed.

## Installation

Connect to the hosted MCP server:

```
https://mcp.rozkoduj.com/mcp
```

No API key required. Works immediately.

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

| Tool | Description |
| ---- | ----------- |
| `scan` | Screen markets with 3000+ fields, 26 filter operators, 78 markets. Filter by any indicator, volume, market cap, and more. |
| `analyze` | Single-symbol technical analysis: composite BUY/SELL/NEUTRAL rating + RSI, MACD, Bollinger Bands, ADX, and 30+ indicators. |
| `movers` | Top gainers and losers across any market. Supports crypto, stocks, forex. |
| `compare` | Side-by-side technical analysis for up to 10 symbols at once. |
| `multitf` | Multi-timeframe analysis with alignment scoring. Default: 15m, 1h, 4h, 1d, 1W. |

## Example Prompts

```
Scan crypto for RSI below 30 with rising volume
Analyze BTCUSDT on 4h timeframe
Compare AAPL, MSFT, GOOGL technical indicators
Show me top crypto gainers today
Multi-timeframe analysis for ETHUSDT — is it aligned bullish?
Screen US stocks with market cap above 10B sorted by change
```

## Data

Real-time market data via [rozkoduj](https://rozkoduj.com) data API. No API key. No paid feeds.

Auto-detects exchanges — `BTCUSDT` resolves to Binance, `AAPL` to NASDAQ, `EURUSD` to Forex.

## Self-Hosting

> **Note:** PyPI package not yet published. Use Docker or install from source.

```bash
# Docker (recommended)
docker build -t rozkoduj-mcp .
docker run -p 8080:8080 rozkoduj-mcp

# From source (stdio)
uv run rozkoduj-mcp

# From source (remote, streamable-http)
MCP_TRANSPORT=streamable-http PORT=8080 uv run rozkoduj-mcp
```

## License

MIT — [rozkoduj](https://github.com/rozkoduj) · [rozkoduj.com](https://rozkoduj.com)
