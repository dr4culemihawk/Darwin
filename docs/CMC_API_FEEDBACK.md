# CoinMarketCap API feedback — from building Darwin

Everything below was observed against the live `pro-api.coinmarketcap.com` while
building Darwin for **"Build with CMC" Round 2** (November 2026), on the **Startup**
plan (15,000 credits/month, 50 req/min). Each item is reproducible from this repo:
the calls are in `darwin/cmc/client.py` and the captures in
[`api-evidence/`](api-evidence/README.md).

Written as feedback, not complaints — Darwin works around every item, and the
workarounds are what the docs describe.

---

## 1. `ohlcv/historical` is not on the Startup tier, but `/quotes/historical` is

**Observed:** `/v2/cryptocurrency/ohlcv/historical` returns error **1006** (not
available on the current plan). The same is true of `/v1/exchange/listings/latest`
and `/v1/cryptocurrency/trending/latest`. `/v2/cryptocurrency/quotes/historical`
*does* work.

**Why it matters:** true OHLCV candles are the natural input for any backtester —
intrabar highs/lows are what make stop-loss and take-profit rules realistic.
Without them, a backtest can only fill stops on close-to-close moves, which
understates drawdowns in fast markets.

**Impact on Darwin:** the `auto` source chain falls back to daily snapshots from
`quotes/historical`, synthesising `open` as the prior close and bounding
`high`/`low` by the two snapshot values. That is honest but lossy, and the code says
so in `quotes_historical_daily`'s docstring.

**Suggestion:** either surface a "candles: not included" line in the plan matrix
next to the endpoint, or expose `interval=hourly` OHLCV on Startup.

---

## 2. History depth is 12 months across several "historical" endpoints — including RWA

**Observed:**

- `/v1/global-metrics/quotes/historical` → error **1014** beyond ~364 days.
- `/v2/cryptocurrency/quotes/historical` → caps at 12 months.
- `/v5/real-world-assets/quotes/historical` → caps at 12 months, despite the RWA
  documentation describing daily history going back further. Darwin clamps every
  lookback to 364 days (`HISTORY_LOOKBACK_DAYS`) to avoid burning failed requests.

**Why it matters:** 12 months is a very short backtest. It contains exactly one
market regime, so a strategy validated on it is validated on one story. Our own
locked champion is a case in point: it traded well on a 24-month window captured
earlier in 2026, and barely trades in the last 12 months of range/bear conditions.
That is *information about the market*, not a bug — but it only becomes visible
with a longer window.

**Suggestion:** document the cap per endpoint and per tier in one table, and return
the cap in the 1014 error body so clients can clamp programmatically instead of
guessing.

---

## 3. `global-metrics/historical` defaults `count` to 10 and says nothing about it

**Observed:** with `time_start` set and no `count`, the endpoint returns **10**
points — silently. A caller requesting a year of daily dominance gets ten days and
no warning.

**Impact on Darwin:** `global_metrics_historical()` always passes `count`
explicitly (`days + 1`). This one is easy to miss because the response is valid
JSON with a `status.error_code` of 0.

**Suggestion:** default to the full requested window, or echo the effective
`count` back in the response.

---

## 4. RWA screener sorting and missing fields

**Observed** on `/v5/real-world-assets/assets/list`:

- `sort=tokenized_market_cap` returns **$0-cap assets first**, so the top of the
  list is the least useful part of it.
- There is no yield / AUM / issuer aggregation field on the asset object.
- `asset_type=government_security` returns **0 assets**, while the type clearly
  exists in the taxonomy.
- The 24h-volume sort *does* behave sensibly, which is what Darwin uses
  (`sort=tokenized_volume_24h`).

**Impact on Darwin:** the RWA panel sorts client-side (by market cap for the issuer
breakdown, by volume for the leaderboard) and treats a tokenized market cap of 0 as
"no capital" rather than "top of list".

**Suggestion:** make the zero-cap rows sort last for any sort key, and return an
empty result *with* an explanation for taxonomy entries with no listed assets.

---

## 5. `/v4/dex/listings/quotes` returned 500

**Observed:** a plain `GET /v4/dex/listings/quotes` returned **HTTP 500** without a
CMC error body (several attempts, different params). Not pagination-related as far
as we could tell.

**Impact on Darwin:** none — we dropped the endpoint and used the v5 RWA quotes
instead. Reporting it in case the v4 DEX surface is unused and quietly broken.

---

## 6. Fear & Greed details worth documenting

Three small things cost real debugging time:

1. **`timestamp` is a string-encoded epoch** (`"1795392000"`), not an integer. Pandas'
   `to_datetime(unit="s")` on strings yields all-`NaT` rather than an error, which
   silently produced an unsorted series — and the "latest" Fear & Greed value read
   as months old. Coercing to numeric first (`pd.to_numeric`) fixes it. (Fixed in
   `client.py:fear_greed_historical`.)
2. **Results are newest-first**, opposite to most CMC history endpoints.
3. **`limit` caps at 500**; asking for 1000 returns a 400.

**Suggestion:** return an integer epoch (or ISO-8601) and document the ordering and
the cap alongside the endpoint.

---

## What we'd love to see

- **A stale-able `last_updated` on every historical response**, so a client can tell
  whether the newest bar is today's or a cached one. Darwin now rejects candle
  series whose last bar is older than 3 days, because a cached response *looks*
  identical to a live one.
- **Intrabar OHLCV on Startup.** It is the single biggest upgrade to backtest
  realism available here.
- **`/v1/global-metrics/quotes/historical` returning altcoin dominance as a field**
  (it is derivable from BTC + ETH dominance, but every client re-derives it).

---

## Credit notes (for other builders)

- The full Darwin evidence pack — 9 endpoints covering global metrics, RWA, CMC100,
  Fear & Greed and key info — costs **9 credits** total.
- A full evolution run over 8 symbols x 364 daily bars costs **8 requests** for
  candles (one per symbol), thanks to caching in `data/cache/`.
- Cache TTLs that worked well: 60s live quotes, 6h daily history, 24h issuer directory.
