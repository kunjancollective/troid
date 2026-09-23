# troid MCP server

Prop-firm risk and compliance as tools, for any MCP client.

Connect alongside a market-data server (TradingView) and your assistant can size a setup
against the real rule set and check it for disqualification risk, in conversation.

## Tools

| tool | what |
|---|---|
| `check_budget` | Both loss ceilings, which one binds, the crossover equity |
| `size_trade` | Verdict, size, margin, fee share, losses remaining — net of fees |
| `check_compliance` | Tiered hold limit, margin concentration, simultaneous trades, min days, account limits, marketed strategies — with ToU section refs; also states two prohibitions a plan cannot show (strategy switching between assessment and funded, 14(d)(ix); opposite positions across connected accounts, 13(c)(v)) |
| `explain_rule` | Rule mechanics with the arithmetic. 14 topics |
| `list_profiles` | Rule sets modelled, with room-before-max-loss for each |

## Install

```bash
pip install "mcp[cli]"
```

Claude Desktop — add to `claude_desktop_config.json`:

```json
{ "mcpServers": { "troid": { "command": "python3",
    "args": ["/absolute/path/to/troid/mcp/server.py"] } } }
```

## What it will not do

Generate entry signals. Place orders. Touch credentials.

The first is a product decision with a contractual basis: Bitfunded ToU 14(d)(v)
prohibits using third-party or marketed strategies to pass an evaluation, so a signal
tool would put users in breach of the agreement they signed. troid evaluates the idea
you bring; it does not produce one.

## Verified

`size_trade` reproduces `scripts/risk.py` exactly on its reference cases, including the
one where equity sits below the crossover and the max-drawdown ceiling binds instead of
the daily: quantity 1.6220951, notional 126,315.79, fees 101.05 (21.05% of risk),
losses remaining 4.
