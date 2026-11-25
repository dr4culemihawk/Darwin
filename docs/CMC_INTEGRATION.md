# CoinMarketCap integration map

Every live number in Darwin comes from `pro-api.coinmarketcap.com`. This page maps
each endpoint to the code that calls it and the feature it powers, and marks what
was **added for "Build with CMC" Round 2**.

Real captured responses for every endpoint below (9 of them) live in
[`api-evidence/`](api-evidence/README.md).

## Endpoints

| Endpoint | Round 2? | Code | Powers |
| --- | --- | --- | --- |
| `/v2/cryptocurrency/quotes/historical` | **new** | `darwin/cmc/client.py:quotes_historical_daily` | Daily candles for the whole evolution/backtest loop on the Startup tier (see the note below — `ohlcv/historical` is not available there). |
| `/v2/cryptocurrency/ohlcv/historical` | existing | `client.py:ohlcv_historical` | True OHLCV candles when the plan allows it; first choice in the `auto` source chain. |
| `/v2/cryptocurrency/quotes/latest` | existing | `client.py:quotes_latest` | Live prices. |
| `/v3/fear-and-greed/latest` + `/historical` | existing | `client.py:fear_greed_latest/_historical` | The `fgi` signal (0–100), used directly in strategy conditions and shown live in the dashboard. |
| `/v1/global-metrics/quotes/latest` + `/historical` | **new** | `client.py:global_metrics_latest/_historical` | BTC/ETH dominance, total + altcoin market cap. Source of the `btc_dom` and `dom_trend` signals and the regime radar. |
| `/v5/real-world-assets/quotes/latest` + `/historical` | **new** | `client.py:rwa_quotes_latest/_historical` | Tokenized gold: aggregate price/cap/volume, per-issuer `tokens[]`, and the daily price series behind the `gold_rs` signal. |
| `/v5/real-world-assets/assets/list` | **new** | `client.py:rwa_assets_list` | RWA leaderboard by 24h tokenized volume (equities, ETFs, commodities). |
| `/v5/real-world-assets/issuers/list` | **new** | `client.py:rwa_issuers_list` | Issuer directory (token counts per issuer). |
| `/v3/index/cmc100-latest` | **new** | `client.py:cmc100_latest` | CMC100 index level + 24h change on the regime radar. |
| `/v1/key/info` | **new** | `client.py:key_info` | Plan + credit usage, recorded in the evidence pack so the tier behind each capture is verifiable. |

## The three Round 2 signals

All three are first-class spec signals — a strategy can reference them by name in
any condition, exactly like an indicator:

| Signal | Definition | Code |
| --- | --- | --- |
| `btc_dom` | BTC dominance (%) | `darwin/regime.py:regime_series` |
| `dom_trend` | 30-day change in BTC dominance (percentage points) | same |
| `gold_rs` | 30-day total-crypto-market-cap return **minus** 30-day tokenized-gold return | same |

`regime_series` is the single definition: `darwin/data_source.py` imports it for the
backtest signal series, and `darwin/regime.py` uses it for the live radar — so the
number a strategy trains on and the number the dashboard shows can never diverge.

## Data provenance is visible, not implied

- `darwin/data_source.py:LAST_PROVENANCE` records which source served each symbol
  (`cmc_quotes`, `ohlcv`, `binance`, `synthetic`).
- `LAST_NOTES` records *why* a source was skipped — including the freshness guard:
  a cached candle series whose last bar is more than 3 days old is rejected rather
  than silently presented as today's market (`MAX_STALENESS_DAYS`).
- Regime payloads carry `source` and a per-component `provenance` map, and the
  dashboard renders both.

## Credit discipline

Responses are cached in `data/cache/` with per-endpoint TTLs (60s for live quotes,
6h for daily history, 24h for the issuer directory) so repeated backtests do not
re-bill the same candles. The whole evidence pack above costs 9 requests.
