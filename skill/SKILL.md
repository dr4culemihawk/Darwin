---
name: darwin-strategy-foundry
description: >-
  Turn CoinMarketCap market data into a backtestable crypto trading strategy by
  evolving a population of strategy specs with Claude and scoring them on a
  deterministic backtester (risk-adjusted return, drawdown, rule adherence).
  Use when a user wants a trading strategy, a backtest, or a tunable strategy
  spec for BSC / crypto markets — blending indicators (SMA, EMA, RSI, MACD, ROC)
  with CMC's Fear & Greed sentiment and cross-market regime signals (BTC
  dominance, Crypto-vs-gold, market breadth) into entry/exit rules.
license: MIT
allowed-tools: [evolve_strategy, backtest_spec, spec_schema, market_regime, rwa_snapshot, todays_signal]
---

# Darwin — Strategy Foundry Skill

A CMC Skill that authors **backtestable trading-strategy specs** from
CoinMarketCap data. Darwin does not just generate one strategy — it *evolves a
population*, validates the champion **out-of-sample**, and returns it with a full
backtest report.

## Run as an MCP skill (marketplace-native)

Darwin is callable from any MCP client (Claude Desktop, Cursor, the CMC Agent
Hub `find_skill` router) — see `skill.json` and `mcp_config.json`.

```bash
pip install "mcp>=1.2.0"        # the optional `skill` extra
python -m darwin.mcp_server      # exposes the six tools below
```

Tools:
- **`evolve_strategy`** — evolve a champion from CMC data with train / validation /
  **held-out test** scoring. Returns the spec + in-sample vs out-of-sample metrics.
- **`backtest_spec`** — backtest any StrategySpec (deterministic, lookahead-free).
- **`spec_schema`** — return the StrategySpec DSL guide.
- **`market_regime`** *(new, Round 2)* — cross-market regime radar from CMC global
  metrics + RWA + the CMC100 index, with a plain-language risk-on/off label.
- **`rwa_snapshot`** *(new, Round 2)* — tokenized gold aggregate plus the per-issuer
  breakdown (XAUt, PAXG, ...) with market-cap share, and the RWA volume leaderboard.
- **`todays_signal`** *(new, Round 2)* — evaluate a spec's own rules on the latest
  closed bar: per-symbol enter / exit / flat, with every condition's operands and
  truth value.

## When to use this skill

- "Build me a momentum strategy for BTC/ETH/BNB."
- "Give me a backtestable spec that blends RSI, MACD, and Fear & Greed."
- "Evolve a low-drawdown strategy and show the metrics."
- "Backtest this strategy idea on CoinMarketCap data."

## How to run it

```bash
# Evolve a champion strategy (uses CMC data + Claude if keys are set,
# deterministic synthetic data + operators otherwise):
python -m darwin.cli evolve --universe BTC,ETH,BNB,SOL --generations 8

# Backtest a specific spec file:
python -m darwin.cli backtest --spec strategies/sample-champion.json
```

Outputs land in `runs/<id>/`: `champion.json` (the spec), `report.md` (metrics +
equity curve + lineage), `leaderboard.json`, `history.json`, `equity.csv`.

## The strategy spec format

A spec is plain JSON — readable, reproducible, and executable. The backtester is
the single source of truth for what it means.

```json
{
  "name": "MACD + RSI + Fear&Greed",
  "universe": ["BTC", "ETH", "BNB"],
  "timeframe": "1d",
  "indicators": [
    {"id": "macd",     "type": "MACD",        "source": "close", "fast": 12, "slow": 26, "signal": 9},
    {"id": "macd_sig", "type": "MACD_SIGNAL", "source": "close", "fast": 12, "slow": 26, "signal": 9},
    {"id": "rsi",      "type": "RSI",         "period": 14}
  ],
  "entry": {"all": [
    {"left": "macd", "op": "cross_above", "right": "macd_sig"},
    {"left": "rsi",  "op": "<",  "right": 70},
    {"left": "fgi",  "op": ">",  "right": 30}
  ]},
  "exit": {"any": [
    {"left": "macd", "op": "cross_below", "right": "macd_sig"},
    {"left": "fgi",  "op": ">", "right": 82}
  ]},
  "risk": {
    "max_position_pct": 0.25, "max_open_positions": 3,
    "stop_loss_pct": 0.07, "take_profit_pct": 0.22,
    "max_drawdown_pct": 0.30, "trailing_stop_pct": 0.10
  },
  "sizing": {"type": "equal_weight"},
  "rationale": "enter on MACD momentum confirmed by RSI room and non-fearful sentiment"
}
```

### Vocabulary
- **indicators** — `SMA`, `EMA`, `RSI`, `ROC`, `ATR`, `MACD`, `MACD_SIGNAL`, `MACD_HIST`, `PRICE`.
  MACD types use `fast`/`slow`/`signal`; others use `period`.
- **signals** (CoinMarketCap-derived, usable in any condition) — `fgi` = **Fear & Greed
  Index** (0–100); `mom` = cross-sectional market momentum; `breadth` = % of the universe
  above its 50-bar trend; `btc_dom` = BTC dominance (%); `dom_trend` = 30-day change in
  BTC dominance (pp, rising = alt risk-off); `gold_rs` = crypto-vs-tokenized-gold relative
  strength (30-day %, positive = risk-on).
- **price sources** — `open`, `high`, `low`, `close`, `volume`.
- **operators** — `>`, `<`, `>=`, `<=`, `cross_above`, `cross_below`.
- **conditions** — `{"all": [...]}`, `{"any": [...]}`, or a leaf `{"left", "op", "right"}`.
- Strategies are **LONG/FLAT**. Entry opens; exit or a risk rule closes.

## How strategies are scored (the fitness rubric)

The backtester is deterministic and lookahead-free, with PancakeSwap-realistic
fees (0.25%) + slippage. Fitness mirrors the BNB-Hack judging rubric:

- **risk-adjusted** — Sortino + Sharpe (clamped to resist flukes)
- **drawdown** — penalized multiplicatively
- **rule adherence** — squared: strategies that fight their own risk rules are crushed
- **turnover** — penalized: over-trading is discouraged

Reported metrics: total return, CAGR, Sharpe, Sortino, **max drawdown**, Calmar,
win rate, trades, exposure, **rule adherence**.

## Authoring tips for the LLM

- Prefer an economically-grounded edge (trend, mean-reversion, momentum, breakout,
  sentiment) over curve-fit noise.
- Always include sane risk rules: a stop, a take-profit, and a `max_drawdown_pct`
  kill-switch.
- Use `fgi` for contrarian or regime filters (e.g. avoid entries in Extreme Fear,
  trim in Extreme Greed).
- Use `btc_dom` / `dom_trend` / `gold_rs` for cross-market regime filters: e.g. skip
  alt entries while `dom_trend > 1` (capital concentrating in BTC), or demand
  `gold_rs > 0` (crypto beating gold) before taking risk.
- Cross `MACD` over `MACD_SIGNAL` for classic momentum entries; confirm with `rsi`.

## References
- `references/spec-format.md` — full DSL reference
- `darwin/strategy/spec.py` — the authoritative schema + validator
