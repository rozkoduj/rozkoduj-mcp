<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/rozkoduj/rozkoduj-mcp/main/docs/assets/logo-dark.svg">
  <img alt="Rozkoduj MCP" src="https://raw.githubusercontent.com/rozkoduj/rozkoduj-mcp/main/docs/assets/logo.svg" width="240">
</picture>

# Decode the Markets

Market intelligence for your AI assistant - algo-trading strategies, analytics and specialized research knowledge.

[![PyPI](https://img.shields.io/pypi/v/rozkoduj-mcp)](https://pypi.org/project/rozkoduj-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue)](https://python.org)
[![CI](https://img.shields.io/github/actions/workflow/status/rozkoduj/rozkoduj-mcp/ci.yml?branch=main&label=CI)](https://github.com/rozkoduj/rozkoduj-mcp/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/rozkoduj/rozkoduj-mcp)](https://codecov.io/gh/rozkoduj/rozkoduj-mcp)

[![Add to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=rozkoduj&config=eyJ1cmwiOiJodHRwczovL21jcC5yb3prb2R1ai5jb20vbWNwIn0%3D)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_rozkoduj-0098FF?logo=githubcopilot)](https://insiders.vscode.dev/redirect/mcp/install?name=rozkoduj&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fmcp.rozkoduj.com%2Fmcp%22%7D)

</div>

> ### Just ask
>
> - *"What strategy works best on AAPL?"*
> - *"Show me the top strategy's backtest - return, max drawdown, win rate."*
> - *"How risky is BTC?"*
> - *"How do I avoid overfitting a backtest?"*

## Getting started

The hosted server works immediately - no API key, no sign-up. Signing in on a
paid tier adds the deeper knowledge base to research results.

**Standard config** works in most MCP clients:

```json
{
  "mcpServers": {
    "rozkoduj": {
      "url": "https://mcp.rozkoduj.com/mcp"
    }
  }
}
```

<details>
<summary><b>Cursor</b></summary>

Click the **Add to Cursor** button above, or add to `~/.cursor/mcp.json`:

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

Click the **Install in VS Code** button above, use the CLI:

```bash
code --add-mcp '{"name":"rozkoduj","type":"http","url":"https://mcp.rozkoduj.com/mcp"}'
```

or add to `.vscode/mcp.json`:

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

Add `--scope user` to enable it in every project.
</details>

<details>
<summary><b>Claude Desktop / claude.ai</b></summary>

**Settings → Connectors → Add custom connector**, then enter:

```
https://mcp.rozkoduj.com/mcp
```

Connectors are account-level, so the server is available in both the desktop
app and claude.ai. Sign in with Rozkoduj when prompted, or skip it to use the
anonymous tier.
</details>

<details>
<summary><b>ChatGPT</b></summary>

Custom MCP connectors need **Developer mode** (Plus/Pro/Team/Enterprise/Edu):

1. **Settings → Connectors → Advanced** - enable *Developer mode*.
2. **Settings → Connectors → Create** - name it `Rozkoduj`, set the MCP
   server URL to `https://mcp.rozkoduj.com/mcp`, pick *OAuth* (or
   *No authentication* for the anonymous tier), and create.
3. In a chat, open **+ → Developer mode** and toggle Rozkoduj on.
</details>

<details>
<summary><b>Self-hosted (PyPI / Docker)</b></summary>

```bash
uvx rozkoduj-mcp               # run straight from PyPI
pip install rozkoduj-mcp       # or install
docker run -p 8080:8080 $(docker build -q .)  # or containerized
```

Defaults to stdio transport; set `MCP_TRANSPORT=streamable-http` to serve
HTTP. See [Self-host with your own key](#self-host-with-your-own-key) to run
as your subscription tier.
</details>

## How it works

You ask in plain language. The AI picks the right tool. You get an answer with
evidence - strategy metrics you can rank, or research passages you can cite -
not a data dump.

| You ask                                        | You get                                                             |
| ---------------------------------------------- | ------------------------------------------------------------------- |
| *"What strategy works best on AAPL?"*          | Strategies backtested on AAPL, ranked by their score on it          |
| *"Best aggressive strategy right now?"*        | Leaderboard narrowed to the aggressive risk mode, ranked by score   |
| *"How risky is BTC?"*                          | The instrument dossier - volatility, drawdowns, character fingerprint |
| *"What does the research say about position sizing?"* | Ranked passages with `slug` + `locale` for citation          |

## Tools

One tool per pillar. All four are read-only.

- **leaderboard** - the strategy leaderboard: published, backtested
  strategies, ranked. Sort by score or APY; filter by family or by instrument
  symbol ("what works best on AAPL?").
- **strategy** - one strategy's full dossier: metrics, risk mode, parameters,
  and the backtest summary.
- **instrument** - the catalog of covered markets, or one instrument's
  dossier: buy-and-hold facts and the six-axis character fingerprint.
- **research** - one search across the research: articles plus, on paid
  tiers, the deeper knowledge base. Returns cited passages.

## Example prompts

**Explore the leaderboard**
```
What strategy works best on AAPL?
Show me the highest-APY strategy and its max drawdown.
Which strategy family performs best?
```

**Dig into a strategy**
```
Give me the full details on the MA Crossover strategy.
What's the win rate and risk mode of your top strategy?
```

**Explore the markets**
```
Which markets do you cover?
How risky is BTC - volatility, drawdowns, character?
```

**Search the research**
```
How do I avoid overfitting a backtest?
Find articles about position sizing and drawdown control.
```

## Self-host with your own key

The hosted server at `https://mcp.rozkoduj.com/mcp` authenticates to the data
API automatically. When you self-host the package, supply your own Rozkoduj API
key so calls run as your subscription tier instead of the anonymous tier:

1. Mint a key in the Rozkoduj dashboard (format `rzk_` + 40 hex). It maps to
   your account's tier; revoke it there at any time.
2. Provide it via the `ROZKODUJ_API_KEY` environment variable - never inline in
   committed config. In an MCP client, reference it as `${env:ROZKODUJ_API_KEY}`.
3. A malformed value is ignored (requests fall back to anonymous); the active
   posture is logged at startup, prefix only - the key is never logged.

Precedence: `ROZKODUJ_API_KEY` (self-host) > anonymous. The hosted server
authenticates automatically.

## License

MIT - [rozkoduj.com](https://rozkoduj.com)
