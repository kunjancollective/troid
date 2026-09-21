# troid

Risk tooling and published research for prop-firm traders. Currently modelled on
Bitfunded's rule set.

**It never places orders and never touches account credentials.** It does arithmetic on
numbers you give it.

## Why this exists

Across 300,000+ prop accounts, roughly 14% reach a funded account and about 7% ever get
paid. Around 70% of failures are loss-limit breaches, most in the first week — failures
trace to position size, not to strategy selection. Almost everything sold in this niche
is entry signals. This is the other thing.

## Check our numbers before trusting any of them

```bash
cd backtest && python3 verify_claims.py
```

Re-derives every published figure from first principles, independent of the code that
produced it, and tags each with a confidence tier:

| tier | meaning | how we may state it |
|---|---|---|
| `DERIVED` | follows algebraically from the firm's rules | as fact, with the algebra shown |
| `SOURCED` | from firm docs or published industry data | with the citation and section number |
| `MODELLED` | Monte Carlo under stated assumptions | assumptions in the same sentence |
| `MEASURED` | our backtest, one asset, one regime | **never as fact** |

Current state: 0 failed checks. And our best strategy result is `MEASURED`, which is why
we make no claim about it — see below.

## What's here

| path | what |
|---|---|
| `.claude/skills/prop-trading-desk/` | The desk. Sizing against both loss ceilings, journal analysis, market briefs. Auto-loads in Claude Code. |
| `backtest/` | Engines modelling Bitfunded's rules exactly — floating-loss auto-fail, 16:00 UTC reset with rollover, 0.04%/side fees, static floor, 10-day hold cap, 5-day minimum. |
| `backtest/verify_claims.py` | The accuracy ledger. |
| `METHODOLOGY.md` | How numbers get onto a page, the four tiers, firm selection, and every correction since launch. Versioned. |
| `backtest/STRATEGY.md` | The strategy, pinned. `strategy_config.json` is the only place it's configured. |
| `backtest/forward.py` | The shadow: replays the strategy forward, journals trades with timestamps. Places nothing. |
| `backtest/profile_optimizer.py` | Optimal risk per challenge type. |
| `web/` | Public FAQ and strategy dashboard. |
| `prompts/` | Build brief for the TradingView risk overlay. |

## The system, five steps

1. **Get troid.** Free. The calculator at troid.ai, `TROID.md` for any LLM, or the MCP server.
2. **Connect your numbers.** TradingView MCP for price and ATR, or type them in.
3. **Bring a trade.** Entry, stop, side. troid returns size, binding ceiling, fee drag, compliance.
4. **Watch the ledger.** How troid sizes on real bars. Closed trades only — it can't be copied.
5. **Decide.** If a challenge makes sense for you, the affiliate link is how troid stays free.

`TROID.md` is the whole desk as one file. Paste it into any assistant as a system prompt.

## Quick start

```bash
cd .claude/skills/prop-trading-desk
cp config.example.json config.json          # your balances; gitignored
python3 scripts/risk.py --profile 1step budget
python3 scripts/risk.py size --symbol BTCUSDT --side long \
    --entry 78000 --stop-atr 1.5 --atr 2000 --target-r 2
```

Profiles: `1step`, `2step_s1`, `2step_s2`, `trader`.

## Three numbers worth knowing

**Your daily limit often isn't the constraint.** On a $100k 1-Step, below $98,000 of
equity the static 6% floor binds instead, and the advertised 4% daily is fiction. That
crossover is $2,000 from the starting line — half of one bad day.

**Leverage is not risk.** A $500 loss is $500 at 2×, 5× or 25×. Leverage changes margin
and liquidation distance, never the loss. What it changes is whether price can wick
through liquidation before reaching your stop.

**Sizing beats edge.** At +0.35R per trade — better than most professionals sustain —
risking 1% with no cap on remaining budget blows the account 68% of the time within a
year. At 2%, 98%. Under a proportional cap, 0%.

## On our own strategy

We backtested a 4h BTCUSDT system across ~30 configurations under Bitfunded's exact
rules. Best result: +0.038R per trade, n=71, standard error 0.045R, 95% CI
[−0.050R, +0.126R] — contains zero. Under a *true zero edge*, the best of 30
configurations would be expected around +0.119R by chance. Ours is a third of that.

In 70 simulated challenge runs it passed zero times.

We have not run out-of-sample validation. Until we have, and until it's been traded live
with our own money for several months, we claim nothing. If you ever see us claim
otherwise, ask for the out-of-sample numbers.

## Licence

MIT — see LICENSE.
