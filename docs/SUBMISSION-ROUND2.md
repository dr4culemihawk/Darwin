# Submission — "Build with CMC" Round 2

Darwin extends the BNB Hack 2026 Track 2 entry and submits it to **Build with CMC:
API Hackathon, Round 2** (DoraHacks, submissions close **Wed 9 Dec 2026, 23:59 UTC**).

## Rule compliance: what is NEW in Round 2

Round 2 only counts a **pre-existing project** if the CoinMarketCap integration is new and
clearly identified. Every Round 2 addition is labelled in the README
(["New for Build with CMC Round 2"](../README.md#new-for-build-with-cmc-round-2)),
in the code (`NEW` docstrings/markers in `darwin/regime.py`, `darwin/cmc/client.py`,
`darwin/mcp_server.py`), and in the docs.

| Round 2 addition | Proof |
| --- | --- |
| Global metrics endpoints → `btc_dom`, `dom_trend` signals | `darwin/cmc/client.py`, `darwin/regime.py:regime_series` |
| Real-World Assets endpoints → `gold_rs` signal + issuer panel | same, plus `rwa_snapshot` |
| CMC100 index in the regime radar | `client.py:cmc100_latest` |
| 3 new MCP tools (`market_regime`, `rwa_snapshot`, `todays_signal`) | `darwin/mcp_server.py`, `skill/skill.json` v1.1.0 |
| Regime radar + today's-signal + RWA panels on the dashboard | `web/components/RegimeRadar.tsx`, `TodaySignal.tsx`, `RwaPanel.tsx` |
| API evidence pack (9 real responses) + feedback report | `docs/api-evidence/`, `docs/CMC_API_FEEDBACK.md` |
| Freshness guard (stale caches rejected) | `darwin/data_source.py` |

Track choice: **AI Agents & Automation** (Darwin is a callable MCP skill that turns CMC data
into a validated, executable strategy spec — and answers market questions directly).

## Requirements checklist

- [x] **Public repo** — this repository
- [x] **Reproducible** — `requirements.txt` + `.env.example`; `python -m scripts.demo`
      and all four tests run with **no keys** on deterministic synthetic data
- [x] **Uses the CMC API** — 9 endpoints, evidence-captured in `docs/api-evidence/`
- [x] **Skill / agent surface** — `skill/` (SKILL.md + skill.json + mcp_config.json), 6 MCP tools
- [x] **Live results** — dashboard data regenerated from live CMC data
      (`python -m scripts.export_dashboard`), committed at `web/public/data/darwin.json`
- [x] **Feedback to CMC** — `docs/CMC_API_FEEDBACK.md` (6 concrete, reproducible issues)
- [ ] **Demo video** — record with `DEMO.md` (2–3 min); use `python -m darwin.cli regime --rwa`
      on screen for the Round 2 surface
- [ ] **Submit on DoraHacks** — repo + demo link + the blurb below
- [ ] **X post** with `#BuildwithCMC`

## Before submitting (your steps)

1. Fill `.env` with `CMC_PRO_API_KEY` (+ `ANTHROPIC_API_KEY` for live Claude operators).
2. `python -m scripts.export_dashboard` — regenerates the dashboard on fresh CMC data.
3. `python -m scripts.api_evidence` — refreshes the evidence pack with today's responses.
4. `cd web && npm run build` — verify the dashboard builds, then push (Vercel auto-deploys).
5. Record the demo, post on X, submit on DoraHacks.

## DoraHacks blurb (draft — edit freely)

> **Darwin — an evolutionary strategy foundry built on CoinMarketCap.**
>
> Most "AI strategy" tools prompt an LLM once and hand back a single strategy. Darwin
> breeds a *population*: Claude authors candidate strategy specs, a deterministic
> lookahead-free backtester scores each on the judging rubric (Sortino/Sharpe, drawdown,
> and **rule adherence**), and a genetic algorithm evolves the survivors across generations.
> The champion is locked and then **forward-tested on a held-out window it never saw**.
>
> **New in Round 2**, Darwin treats CoinMarketCap's newer data as first-class signal rather
> than decoration: **global metrics** give every strategy two cross-market regime signals
> (`btc_dom`, `dom_trend`), **Real-World Assets** add a third (`gold_rs` — crypto vs
> tokenized gold as a risk-appetite gauge), and the **CMC100 index** anchors a live Regime
> Radar with plain-language risk labels, per-endpoint provenance and a tokenized-gold issuer
> breakdown (XAUt vs PAXG vs …).
>
> All of it ships as a **6-tool MCP skill** — `evolve_strategy`, `backtest_spec`,
> `spec_schema`, plus `market_regime`, `rwa_snapshot` and `todays_signal`, which evaluates a
> strategy's own rules on the latest close and tells you **enter / exit / flat at the next
> open**, with every condition shown.
>
> We also publish what we found: a 9-endpoint **evidence pack** of real captured responses,
> and a written **API feedback report** covering the Startup-tier history caps, a silent
> `count` default, RWA sorting quirks and the Fear & Greed timestamp format. And we publish
> our **failures**: the Round 2 re-evolution produced a candidate that lost 2.3% on the
> held-out window, so we did not adopt it. The champion you see is the one that survived
> out-of-sample testing — including a year where the honest answer was "stay flat".
