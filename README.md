# Rozkoduj MCP

> **Decode the markets with your AI assistant.**
> Screening, analysis, and scoring across stocks, crypto, and forex — exposed as MCP tools.

[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=for-the-badge&logoColor=white)](https://cursor.com/en/install-mcp?name=rozkoduj&config=eyJuYW1lIjoicm96a29kdWoiLCJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vbWNwLnJvemtvZHVqLmNvbS9tY3AifQ==)
[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=for-the-badge&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=rozkoduj&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A//mcp.rozkoduj.com/mcp%22%7D)

[![CI](https://github.com/rozkoduj/rozkoduj-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rozkoduj/rozkoduj-mcp/actions)
[![PyPI](https://img.shields.io/pypi/v/rozkoduj-mcp?style=flat-square)](https://pypi.org/project/rozkoduj-mcp/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue?style=flat-square)](https://python.org)
[![Coverage](https://img.shields.io/codecov/c/github/rozkoduj/rozkoduj-mcp?style=flat-square)](https://codecov.io/gh/rozkoduj/rozkoduj-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## See it in action

```text
You      Should I buy AAPL?

Claude   Calling: score, analyze, buzz, market_pulse...

         AAPL — 59/100 SLIGHT BUY at $263.40

         Technical    BULLISH on weekly · neutral daily · RSI 57 · MACD positive
         Fundamental  P/E 33 · Piotroski 9/9 · 24 buy / 15 hold / 2 sell · +14% to target
         Attention    HIGH · 25 fresh headlines (Yahoo, CNBC, Reuters)
         Market       NEUTRAL regime · VIX 18 · stocks in GREED

         Verdict: trend confirmed across timeframes, fundamentals
         strong but valuation stretched. Buy on pullback rather
         than chase the high.
```

One question, four tool calls, one decision. No browser tabs, no spreadsheet, no API keys.

---

## Why Rozkoduj

|                  |                                                                          |
| ---------------- | ------------------------------------------------------------------------ |
| **No API key**   | Hosted at `mcp.rozkoduj.com/mcp` — works immediately.                    |
| **No setup**     | Streamable HTTP, stateless, JSON. One URL in your MCP client config.     |
| **20+ markets**  | US, UK, EU, India, Japan, Korea, crypto, forex — symbols auto-detected.  |
| **13 tools**     | Screen, analyze, score, decode, multi-timeframe, news, calendar, regime. |
| **Open source**  | MIT, public on GitHub, 100% test coverage, deployed on Cloud Run.        |

---

## How it works

```
   Your AI assistant
   (Claude · Cursor · VS Code)
            │
            │  MCP (streamable-http)
            ▼
     rozkoduj-mcp ──────── public proxy (this repo)
            │
            │  HTTPS
            ▼
   api.rozkoduj.com ────── private data backend
            │
            ▼
     Market data providers
```

**Open-core:** the MCP layer is public so any AI client can use it; the data backend stays private and swappable. No data-source coupling leaks into the public repo.

---

## Quick start

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
<summary><b>Self-hosted (PyPI · Docker)</b></summary>

```bash
pip install rozkoduj-mcp       # from PyPI
uvx rozkoduj-mcp               # or run directly
docker run -p 8080:8080 $(docker build -q .)  # from source
```
</details>

---

## Tools

### Find opportunities

| Tool            | What it does                                                                                                                                                            |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `digest`        | Scans 20+ global markets and surfaces anomalies ranked by 1-5 star surprise score. Volume spikes, RSI extremes, big moves, 52-week breaks — with fundamental context.   |
| `scan`          | Custom screening across 30+ indicators and fundamentals with arbitrary filters.                                                                                         |
| `smart_screen` | One-word presets: `unusual_volume`, `oversold_bounce`, `breakout`, `momentum`, `value`, `dividend`, `growth`.                                                           |
| `movers`        | Top gainers and losers with quality filters.                                                                                                                            |

### Analyze a symbol

| Tool           | What it does                                                                                                                       |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `decode`       | Full 3-D analysis: technical (1d / 4h / 1W), fundamental, news. Each dimension scored 0-100, combined into a verdict.              |
| `score`        | Quick 0-100 score: technical rating, momentum, volume quality, trend strength.                                                     |
| `analyze`      | Detailed TA: RSI, MACD, Bollinger, ADX, EMAs, and 30+ indicators on any timeframe.                                                 |
| `fundamentals` | Valuation (P/E, P/B, EV/EBITDA), quality (Piotroski, Altman Z), analyst consensus, earnings, dividends.                            |
| `compare`      | Side-by-side TA for up to 10 symbols.                                                                                              |
| `multitf`      | Multi-timeframe alignment scoring across 15m, 1h, 4h, 1d, 1W.                                                                      |

### Read the market

| Tool           | What it does                                                          |
| -------------- | --------------------------------------------------------------------- |
| `market_pulse` | Fear & greed indices + VIX → RISK-ON, RISK-OFF, or NEUTRAL.           |
| `buzz`         | News attention signal for any ticker, in any language.                |
| `calendar`     | Upcoming economic events with actual vs forecast vs previous.         |

<details>
<summary><b>Resources &amp; Prompts</b></summary>

| Type     | Name                          | Description                                          |
| -------- | ----------------------------- | ---------------------------------------------------- |
| Resource | `rozkoduj://markets`          | Available markets with IDs                           |
| Resource | `rozkoduj://fields`           | Screening fields by category                         |
| Resource | `rozkoduj://operators`        | Filter operators for scan                            |
| Prompt   | `morning_briefing`            | Daily overview: regime, movers, calendar             |
| Prompt   | `deep_dive(symbol)`           | Full analysis: all tools combined                    |
| Prompt   | `find_opportunities(market)`  | Multi-screen opportunity scan                        |

</details>

---

## Try these prompts

**Should I buy?**
```
Score AAPL — should I buy?
Decode NVDA — full 3-D analysis with news.
Compare AAPL, MSFT, GOOGL — which one looks best?
```

**What's interesting today?**
```
What are today's market anomalies? Any hidden gems?
Find unusual volume stocks in crypto.
Show me oversold bounce candidates in European markets.
```

**What's going on?**
```
Is the market risk-on or risk-off right now?
What economic events are happening this week?
Is there any buzz around Tesla?
```

---

<sub>
Symbols auto-detect: <code>BTCUSDT</code> → crypto · <code>AAPL</code> → US stocks · <code>EURUSD</code> → forex.
<br><br>
License MIT · <a href="https://rozkoduj.com">rozkoduj.com</a> · <a href="https://github.com/rozkoduj/rozkoduj-mcp/issues">Issues</a> · <a href="https://github.com/rozkoduj/rozkoduj-mcp/releases">Releases</a> · <a href="https://pypi.org/project/rozkoduj-mcp/">PyPI</a>
</sub>
