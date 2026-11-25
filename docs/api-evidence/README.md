# CMC API evidence pack

Real responses captured from `pro-api.coinmarketcap.com` on **2026-11-25T10:08:56Z**.
Payloads are trimmed (short lists, long strings cut) — the shapes and fields are unmodified.

| File | Endpoint | Result | What it powers |
| --- | --- | --- | --- |
| [`global-metrics-latest.json`](global-metrics-latest.json) | `/v1/global-metrics/quotes/latest` | ok | Total market cap, BTC/ETH dominance and 24h volume — the headline regime row. |
| [`global-metrics-historical.json`](global-metrics-historical.json) | `/v1/global-metrics/quotes/historical` | ok | Daily dominance + market-cap history behind the btcz_dom and dom_trend signals. |
| [`cmc100-latest.json`](cmc100-latest.json) | `/v3/index/cmc100-latest` | ok | CMC's own 100-asset index level, used in the regime radar. |
| [`rwa-quotes-latest-gold.json`](rwa-quotes-latest-gold.json) | `/v5/real-world-assets/quotes/latest` | ok | Tokenized gold aggregate + per-issuer tokens[] (XAUt, PAXG, ...) for the issuer panel. |
| [`rwa-quotes-historical-gold.json`](rwa-quotes-historical-gold.json) | `/v5/real-world-assets/quotes/historical` | ok | Daily tokenized-gold price — the safe-haven leg of the gold_rs regime signal. |
| [`rwa-assets-list.json`](rwa-assets-list.json) | `/v5/real-world-assets/assets/list` | ok | RWA screener by tokenized volume (equities, ETFs, commodities). |
| [`rwa-issuers-list.json`](rwa-issuers-list.json) | `/v5/real-world-assets/issuers/list` | ok | Issuer directory (token counts per issuer). |
| [`fear-greed-latest.json`](fear-greed-latest.json) | `/v3/fear-and-greed/latest` | ok | CMC's proprietary sentiment index — the fgi signal. |
| [`key-info.json`](key-info.json) | `/v1/key/info` | ok | Plan + credit usage, proving which tier the evidence was captured on. |
