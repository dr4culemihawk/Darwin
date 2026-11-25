<div align="center">

# 🧬 Darwin

### An evolutionary trading-strategy foundry for BNB Chain

*Most "AI strategy" tools prompt an LLM once and hand you a single strategy.*
**Darwin evolves a population — and proves the survivor out-of-sample.**

[![Build with CMC](https://img.shields.io/badge/Build_with_CMC-Round_2-F0B90B?style=flat-square)](https://coinmarketcap.com/api/hackathon/)
[![CoinMarketCap](https://img.shields.io/badge/CoinMarketCap-Agent_Hub-blue?style=flat-square)](https://coinmarketcap.com/api/)
[![On-chain](https://img.shields.io/badge/BNB-ERC--8004_agent_%231467-success?style=flat-square)](https://testnet.bscscan.com/tx/0x8f3c609817ab889d7160d3b4583e4d757bae873456b885d219cf3163ed8fdc7a)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

**[▶ Live dashboard](https://darwin-foundry.vercel.app)**  ·  **[Champion spec](strategies/sample-champion.json)**  ·  **[API evidence pack](docs/api-evidence/README.md)**  ·  **[CMC API feedback](docs/CMC_API_FEEDBACK.md)**

</div>

---

## What it is

Darwin pulls **CoinMarketCap** market data and signals, has **Claude** author candidate
*backtestable strategy specs*, scores each on a **deterministic, lookahead-free backtester**
(risk-adjusted return, drawdown, and adherence to user-defined risk rules), and **evolves**
the survivors across generations into a champion. The champion is **forward-tested on a
held-out window it never saw**, exposed as a callable **CMC Skill (MCP)**, given a verifiable
**on-chain identity** on BNB Chain, and can plan a rule-gated swap via the **Trust Wallet Agent Kit**.

The deliverable is a **backtestable spec, not a live agent** — a readable, reproducible,
executable JSON strategy with a full report, plus the market-intelligence surface built on
CoinMarketCap's newer endpoints.

```
                    ┌──────────────────────── DARWIN ────────────────────────┐
  CoinMarketCap ──► │  quotes + Fear&Greed + global metrics + RWA ─► Claude   │
  (data + signals)  │   (momentum/breadth/btc_dom/dom_trend/gold_rs)  signals │
                    │   ┌──── evolution loop (GA) ──────────────────────┐     │
                    │   │ population ─► deterministic backtest ─►       │     │
                    │   │   fitness (Sortino, drawdown, rule adherence) │     │
                    │   │      ▲                              │ select  │     │
                    │   │  Claude mutate / crossover ◄────────┘         │     │
                    │   └───────────────────────────────────────────────┘     │
                    │            │ champion spec                              │
                    │   ┌────────┼───────────────┬──────────────┬───────────┐ │
                    │   ▼        ▼               ▼              ▼           ▼ │
                    │  out-of-   MCP skill    regime radar   TWAK swap   BNB  │
                    │  sample    (6 tools)    + today's      (rule-     ERC- │
                    │  report                 signal          gated)    8004 │
                    └─────────────────────────────────────────────────────────┘
```

---

## New for "Build with CMC" Round 2

This project began as a BNB Hack Track 2 entry. Everything below was **added for
Round 2** on top of the existing engine — and is labelled as such throughout the code,
docs and dashboard.

| What's new | Where | Why it matters |
| --- | --- | --- |
| **Cross-market regime signals** — `btc_dom`, `dom_trend`, `gold_rs` are first-class spec signals any strategy can gate on | `darwin/regime.py`, `darwin/strategy/spec.py` | Strategies now trade *regime*, not just price: skip alt entries while capital concentrates in BTC, or demand crypto beat gold before taking risk |
| **Regime Radar** — BTC/ETH dominance, 30-day dominance trend, total/altcoin market cap, CMC100 index, tokenized gold, with a plain-language risk label and per-endpoint provenance | `/v1/global-metrics/*`, `/v3/index/cmc100-latest`, `/v5/real-world-assets/*` | A macro read anyone can audit: every number shows the endpoint it came from |
| **Today's champion signal** — the champion's own condition tree evaluated on the latest closed bar, per symbol, with every operand and truth value | `darwin/regime.py:champion_signal`, `todays_signal` MCP tool | Turns "a strategy" into an answer: *enter / exit / flat at the next open*, and it can't drift from what a backtest would say — it calls the same `eval_condition` |
| **Tokenized-gold issuer panel** — XAUt vs PAXG vs … market-cap shares, plus an RWA leaderboard by 24h tokenized volume | `/v5/real-world-assets/quotes/latest`, `/assets/list` | The safe haven, on-chain: who issues it, how concentrated it is, what real capital is doing |
| **3 new MCP tools** — `market_regime`, `rwa_snapshot`, `todays_signal` | `darwin/mcp_server.py`, `skill/` | The Round 2 surface is callable by any agent, not just rendered |
| **API evidence pack + feedback** — 9 real captured responses and a written report of API quirks found | `scripts/api_evidence.py`, `docs/` | Claims are verifiable, and the feedback is what Round 2 asks builders for |
| **Freshness guard** — candle sources whose last bar is >3 days old are rejected, never passed off as today's market | `darwin/data_source.py` | A stale cache looks identical to a live response; this is how we stopped shipping June candles |

---

## Why this should be a strong submission

Judged like quant research — *returns, drawdown, risk-adjusted performance, rule
adherence, on a held-out market window* — here is how Darwin answers each:

| Judging dimension | How Darwin answers it |
| --- | --- |
| **Held-out / not overfit** | The champion is locked, then scored on a **held-out window it never saw** (`darwin/validation.py`). Warmup-aware: the test window warms indicators on prior bars but counts no trades or equity before its start. Most entries report 100% in-sample numbers — Darwin shows the split. |
| **Risk-adjusted performance** | Fitness blends Sortino + Sharpe (clamped), a multiplicative drawdown penalty, and turnover penalties — so champions are coherent and low-churn, not lucky one-trade flukes. |
| **Drawdown** | The backtester runs a real risk engine (per-position stops/take-profits, trailing stops, a portfolio max-drawdown kill-switch). |
| **Rule adherence** | User risk rules are first-class and scored: adherence is **squared** in fitness, so a strategy that fights its own rules is crushed. |
| **CMC-native, Round 2 depth** | Daily candles, the proprietary **Fear & Greed Index**, **global metrics** (BTC dominance + trend), **tokenized gold** (crypto-vs-gold risk appetite), the **CMC100 index** and the **RWA screener** — 9 documented endpoints, evidence-pack captured. |
| **Deliverable format** | A backtestable JSON spec **and** a **6-tool MCP Skill** any agent or the CMC Agent Hub can invoke — including three tools that answer market questions directly. |
| **Honesty** | Failed experiments are written down, not buried: the Round 2 re-evolution is below, including the candidate we rejected. |

---

## The result — and what the data actually says

The locked champion (`strategies/sample-champion.json`, fingerprint `10966ca20775`) is a
**dual-MA trend follower with a 100-EMA macro-regime filter, RSI floor and MACD
confirmation**, over 8 majors.

Run on the **freshest 12 months of CoinMarketCap daily data** (364 bars,
2025‑11‑27 → 2026‑11‑25, all 8 symbols served by `cmc_quotes`):

| | Full window | Held-out half (after 2026‑05‑28) |
| --- | --- | --- |
| Return | +0.4% | +0.4% |
| Sharpe | 0.56 | 0.79 |
| **Max drawdown** | **−0.2%** | **−0.2%** |
| **Rule adherence** | **100%** | **100%** |
| Trades | 4 | 4 |
| Exposure | 0.8% | 1.6% |

**Read that honestly.** Four trades in a year and under 1% of market cap moved. In the
window Darwin measured, the total crypto market cap fell ~23% and CMC's Fear & Greed sat
at **9 — Extreme Fear**. For a long/flat trend system, the correct behaviour in a
sustained downtrend is to *stay flat*, and that is exactly what it did: the first half of
the holdout contains **zero trades** because the regime filter refused to enter.

This is a capital-preservation result, not a return story. We would rather show it than
quote a number we can no longer reproduce.

### The earlier +13.1% figure, and why it is not the headline

An earlier run of the same spec reported **+13.1% / Sharpe 1.58 / −1.1% max drawdown** over
a ~24-month daily OHLCV window. That window came from `/v2/cryptocurrency/ohlcv/historical`,
which **the Startup tier no longer serves** (error 1006), and the `quotes/historical`
endpoint that does work is capped at **12 months** (see
[`docs/CMC_API_FEEDBACK.md`](docs/CMC_API_FEEDBACK.md)). The figure is preserved as history
in `runs/`, but it is not the headline, because a judge cannot reproduce it today.

### The Round 2 re-evolution (including the failure)

We re-ran the evolution on the fresh 12-month CMC window with all six signals available
(8 generations, 8 symbols, Claude as operator — `runs/run_67846be0ce68/report.md`). The GA's
best *train* fitness climbed from 0.110 to **0.613**, and the best-validated candidate scored
**+5.3% on the validation window** — then lost **−2.3% on the held-out test window**.

So it was **not adopted**. The previously locked champion was kept. A pipeline that changes
its champion every time the training loss improves is exactly the overfitting this project
exists to avoid.

→ `strategies/sample-champion.json` · `web/public/data/darwin.json` (the dashboard's source of truth)

---

## How it works

**1. Evolutionary, not single-shot.** A genetic algorithm searches over an LLM-authored
strategy DSL. Deterministic operators (mutate/crossover) run every generation for free and
reproducibly; Claude injects creative diversity and metric-guided "insight" mutations of the
champion. The GA *breeds* hybrids. *(`darwin/evolve/`)*

**2. Deterministic, lookahead-free backtester.** Signals form on the close of bar *t−1*,
orders execute at the open of bar *t*, stops/take-profits check bar *t*'s high/low, equity
marks at the close — no same-bar fills, no look-ahead. PancakeSwap-realistic fees (0.25%) +
slippage on every leg. *(`darwin/strategy/backtest.py`)*

**3. Out-of-sample validation.** `run_backtest(trade_from=…)` lets a held-out window warm up
its indicators on prior bars but only counts trades and equity from the window's start — a
true forward test with no cold-start and no leakage. *(`darwin/validation.py`)*

**4. Risk-aware fitness.** Sortino + Sharpe (clamped), a drawdown penalty, **squared**
rule-adherence, and turnover / min-trade penalties. *(`fitness_score`)*

### The strategy spec (DSL)

A spec is plain, executable JSON — readable by a human, generatable by an LLM, and the
backtester is the single source of truth for what it means:

```json
{
  "name": "MACD + RSI + Fear&Greed",
  "universe": ["BTC", "ETH", "BNB"],
  "timeframe": "1d",
  "indicators": [
    {"id": "macd", "type": "MACD", "fast": 12, "slow": 26, "signal": 9},
    {"id": "rsi",  "type": "RSI",  "period": 14}
  ],
  "entry": {"all": [
    {"left": "macd", "op": "cross_above", "right": "macd_sig"},
    {"left": "breadth", "op": ">", "right": 50},
    {"left": "fgi", "op": ">", "right": 30},
    {"left": "gold_rs", "op": ">", "right": 0}
  ]},
  "exit": {"any": [{"left": "fgi", "op": ">", "right": 82}]},
  "risk": {"stop_loss_pct": 0.07, "take_profit_pct": 0.22, "max_drawdown_pct": 0.30, "trailing_stop_pct": 0.10},
  "sizing": {"type": "equal_weight"},
  "rationale": "MACD momentum, confirmed by breadth, neutral sentiment and crypto beating gold"
}
```

**Signals** available to any condition:

| Signal | Meaning | Round 2 |
| --- | --- | --- |
| `fgi` | CMC Fear & Greed Index (0–100) | |
| `mom` / `breadth` | Cross-sectional momentum; % of universe above its 50-bar trend | |
| `btc_dom` | BTC dominance (% of total crypto market cap) | **new** |
| `dom_trend` | 30-day change in BTC dominance (pp; rising = alt risk-off) | **new** |
| `gold_rs` | 30-day crypto-market-cap return minus tokenized-gold return (%; positive = risk-on) | **new** |

All three Round 2 signals come from `darwin/regime.py:regime_series` — the *single*
definition used by both the backtester and the live radar, so training data and displayed
data can never disagree.

---

## The Regime Radar and the RWA panel

Two dashboard surfaces exist purely to make CoinMarketCap's newer data legible:

- **Regime Radar** (`/regime` section): BTC dominance with its 30-day trend, ETH dominance,
  total and altcoin market cap, the **CMC100** index and 24h change, and tokenized gold as
  the safe haven. A two-axis rule — dominance trend × crypto-vs-gold — produces a plain
  label (*risk-on / risk-off / neutral*) with documented thresholds, and every row shows the
  endpoint it came from. Captured 2026‑11‑25: *"Alt rotation, but defensive"* — dominance
  falling (58.61%, −1.42pp/30d) while gold still leads crypto (−12.1pp), i.e. rotation without
  risk appetite.
- **Today's champion signal**: the champion's own rules evaluated on the latest close —
  per-symbol **ENTER / EXIT / FLAT**, with each condition's operands and truth value, and
  honest `unknown` (not a silent `false`) when a required series has no history yet.
- **Tokenized gold issuers**: aggregate price/cap/volume plus the issuer breakdown with
  market-cap share (XAUt ≈61%, PAXG ≈37% at capture) and an RWA leaderboard by 24h
  tokenized volume.

Both are reproducible offline: `python -m darwin.cli regime --rwa` prints exactly what the
dashboard renders.

---

## A callable Marketplace skill (MCP)

Darwin isn't just a CLI — it's a **CoinMarketCap Skill**. Any MCP client (Claude Desktop,
Cursor, the CMC Agent Hub's `find_skill` router) can call it:

```bash
pip install "mcp>=1.2.0"
python -m darwin.mcp_server          # exposes the tools below over MCP (stdio)
```

| Tool | What it does |
| --- | --- |
| `evolve_strategy` | Evolve a champion from CMC data with train / validation / **held-out test** scoring. |
| `backtest_spec` | Backtest any StrategySpec — deterministic, lookahead-free, fees + slippage. |
| `spec_schema` | Return the StrategySpec DSL guide. |
| `market_regime` | **New Round 2** — cross-market regime radar + plain-language risk label. |
| `rwa_snapshot` | **New Round 2** — tokenized gold aggregate, per-issuer shares, RWA volume leaderboard. |
| `todays_signal` | **New Round 2** — per-symbol enter / exit / flat from a spec's own rules, with a full rule breakdown. |

Packaging: `skill/SKILL.md` (frontmatter + `allowed-tools`), `skill/skill.json` (marketplace
manifest, v1.1.0), `skill/mcp_config.json` (wires both the Darwin server and the CMC Data MCP).

---

## Quickstart

```bash
python -m venv .venv && . .venv/Scripts/activate     # macOS/Linux: . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                  # fill in keys (all optional — see below)

# Evolve a champion (works fully offline on deterministic synthetic data with no keys):
python -m darwin.cli evolve --universe BTC,ETH,BNB,SOL --generations 8

# Backtest any spec:
python -m darwin.cli backtest --spec strategies/sample-champion.json

# Regime radar + today's champion signal + tokenized-gold issuers (Round 2):
python -m darwin.cli regime --rwa

# Capture real CMC responses as the evidence pack (Round 2):
python -m scripts.api_evidence

# Dry-run execution (evaluates the live signal, plans a rule-gated swap):
python -m darwin.cli execute --spec strategies/sample-champion.json

# Serve Darwin as a callable CMC Skill over MCP:
pip install "mcp>=1.2.0" && python -m darwin.mcp_server
```

`.env` keys — **all optional.** With none set, Darwin falls back to deterministic synthetic
data + operators, so it *always* runs; keys upgrade it to live:

| Key | Unlocks |
| --- | --- |
| `ANTHROPIC_API_KEY` (+ optional `ANTHROPIC_BASE_URL`, `DARWIN_MODEL`) | live Claude strategy generation + evolution |
| `CMC_PRO_API_KEY` | live CoinMarketCap quotes, Fear & Greed, global metrics, RWA |
| `BSC_PRIVATE_KEY` | BNB on-chain identity registration (use a **testnet** key) |
| `TWAK_ACCESS_ID` / `TWAK_HMAC_SECRET` | Trust Wallet gateway swap routes |

---

## The live dashboard

A premium, mobile-first dashboard renders the locked champion on real data — equity curve
with the out-of-sample boundary marked, in-sample vs held-out comparison, the evolution
timeline, live CMC Fear & Greed, the **Round 2 regime radar and today's signal**, the
**tokenized-gold issuer panel**, and the on-chain identity. It also has a live **"Evolve
live"** button that runs Claude as the GA's mutate operator on the spot.

```bash
cd web && npm install && npm run dev     # http://localhost:3000
```

Deploys to Vercel (root directory `web`). Next.js + Tailwind + Recharts. Regenerate its data
with `python -m scripts.export_dashboard` (pins the CMC-only source and rejects stale caches).

---

## The three sponsor integrations

### 🧠 CoinMarketCap AI Agent Hub
- **Round 1:** daily candles (`/v2/cryptocurrency/quotes/historical`, with OHLCV where the
  plan allows), quotes, and the proprietary **Fear & Greed Index** (`/v3/fear-and-greed`).
- **New in Round 2:** **global metrics** (`/v1/global-metrics/quotes/latest|historical`) →
  the `btc_dom` / `dom_trend` signals; **Real-World Assets**
  (`/v5/real-world-assets/quotes/latest|historical`, `/assets/list`, `/issuers/list`) →
  the `gold_rs` signal and the issuer panel; the **CMC100 index**
  (`/v3/index/cmc100-latest`); and `/v1/key/info` to record which plan the evidence came from.
- **Proof, not claims:** 9 real captured responses in [`docs/api-evidence/`](docs/api-evidence/README.md),
  the full endpoint→code map in [`docs/CMC_INTEGRATION.md`](docs/CMC_INTEGRATION.md), and a
  written [API feedback report](docs/CMC_API_FEEDBACK.md).

### 🛠️ BNB AI Agent SDK
- `darwin/identity/bnb.py` registers Darwin's verifiable **ERC-8004 on-chain identity** on BSC
  testnet via the official `bnbagent` SDK (gas-sponsored).
- **Live on-chain proof:** agentId `1467`, registry `0x8004A818BFB912233c491871b3d84c89A494BD9e` — [tx on BSC testnet ↗](https://testnet.bscscan.com/tx/0x8f3c609817ab889d7160d3b4583e4d757bae873456b885d219cf3163ed8fdc7a).

### 🔐 Trust Wallet Agent Kit
- `darwin/execute/twak_gateway.py`: a **live HMAC-authenticated** client for the TWAK gateway
  (`tws.trustwallet.com`) — correct request signing (RFC-2822 date, sorted-query
  `METHOD;PATH;QUERY;ACCESS_ID;NONCE;DATE`), live BSC asset resolution (`/v1/search/assets`),
  and PancakeSwap route requests.
- *Status:* auth + live asset resolution work on portal credentials; swap-route computation
  returns a server-side error on the free portal tier, so `execute` shows a dry-run plan.

---

## What's real vs simulated (transparency)

| | Status |
| --- | --- |
| Evolution, backtester, fitness, out-of-sample split | ✅ real, deterministic, reproducible |
| Champion metrics in this README and the dashboard | ✅ from live CMC daily data (12-month Startup-tier window) |
| CMC daily candles, Fear & Greed, global metrics, RWA, CMC100 | ✅ live API (9 endpoints evidence-captured) |
| Round 2 regime radar + today's signal | ✅ live, with per-endpoint provenance |
| On-chain ERC-8004 identity | ✅ real BSC-testnet transaction (agent #1467) |
| 6-tool MCP skill | ✅ callable |
| Round 2 re-evolved candidate | ⚠️ rejected — lost −2.3% on the held-out test window (reported, not adopted) |
| TWAK swap execution | ⚠️ auth + asset resolution live; route computation gated on portal tier → dry-run plan |

---

## Repo layout

```
darwin/
  strategy/      spec DSL, indicators (incl. MACD), backtester, metrics
  cmc/           CoinMarketCap client (quotes, OHLCV, Fear & Greed, global metrics, RWA, CMC100)
  regime.py      NEW: cross-market regime radar, today's champion signal, RWA snapshot
  evolve/        seeds, deterministic GA operators, LLM operators, engine
  validation.py  out-of-sample train/validation/test + holdout (no look-ahead)
  data_source.py data chain (cmc_quotes → ohlcv → binance → synthetic) + freshness guard
  execute/       TWAK gateway + execution adapter
  identity/      BNB ERC-8004 on-chain identity
  mcp_server.py  Darwin as a 6-tool MCP Skill
  cli.py         evolve / backtest / regime / execute / register
skill/           SKILL.md + skill.json + mcp_config.json — the CMC Skill package
strategies/      a sample evolved champion + its report
docs/            CMC integration map, API feedback, api-evidence/ (9 real payloads)
scripts/         smoke / evolution / out-of-sample / regime tests, dashboard export, evidence capture
web/             the live Next.js dashboard
```

## Tests

```bash
python -m scripts.smoke_test     # deterministic core on synthetic data
python -m scripts.evolve_test    # offline GA convergence (asserts a usable champion)
python -m scripts.oos_test       # out-of-sample split is sound + lookahead-free
python -m scripts.regime_test    # NEW: regime math, classification, today's signal, freshness guard
```

---

<div align="center">

**Built for "Build with CMC" Round 2 · extends the BNB Hack 2026 Track 2 entry.**  ·  MIT licensed.

</div>
