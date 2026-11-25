"""Capture real CoinMarketCap API responses as an evidence pack for judges.

Writes trimmed, real payloads to docs/api-evidence/ — one JSON file per endpoint
plus an index — so the docs can show *actual* CMC responses rather than claims.
The API key is never written: only the endpoint, the parameters, and the data.

Run:  python -m scripts.api_evidence
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from darwin.cmc.client import CMCClient, CMCError
from darwin.config import ROOT, settings

OUT = ROOT / "docs" / "api-evidence"

# (slug, endpoint, why it matters, callable)
CASES = [
    (
        "global-metrics-latest",
        "/v1/global-metrics/quotes/latest",
        "Total market cap, BTC/ETH dominance and 24h volume — the headline regime row.",
        lambda c: c.global_metrics_latest(),
    ),
    (
        "global-metrics-historical",
        "/v1/global-metrics/quotes/historical",
        "Daily dominance + market-cap history behind the btcz_dom and dom_trend signals.",
        lambda c: c.global_metrics_historical(),
    ),
    (
        "cmc100-latest",
        "/v3/index/cmc100-latest",
        "CMC's own 100-asset index level, used in the regime radar.",
        lambda c: c.cmc100_latest(),
    ),
    (
        "rwa-quotes-latest-gold",
        "/v5/real-world-assets/quotes/latest",
        "Tokenized gold aggregate + per-issuer tokens[] (XAUt, PAXG, ...) for the issuer panel.",
        lambda c: c.rwa_quotes_latest("GOLD"),
    ),
    (
        "rwa-quotes-historical-gold",
        "/v5/real-world-assets/quotes/historical",
        "Daily tokenized-gold price — the safe-haven leg of the gold_rs regime signal.",
        lambda c: c.rwa_quotes_historical("GOLD"),
    ),
    (
        "rwa-assets-list",
        "/v5/real-world-assets/assets/list",
        "RWA screener by tokenized volume (equities, ETFs, commodities).",
        lambda c: c.rwa_assets_list(limit=10),
    ),
    (
        "rwa-issuers-list",
        "/v5/real-world-assets/issuers/list",
        "Issuer directory (token counts per issuer).",
        lambda c: c.rwa_issuers_list(limit=10),
    ),
    (
        "fear-greed-latest",
        "/v3/fear-and-greed/latest",
        "CMC's proprietary sentiment index — the fgi signal.",
        lambda c: c.fear_greed_latest(),
    ),
    (
        "key-info",
        "/v1/key/info",
        "Plan + credit usage, proving which tier the evidence was captured on.",
        lambda c: c.key_info(),
    ),
]


def _trim(obj, depth: int = 0, max_list: int = 3, max_str: int = 220):
    """Keep payloads readable: short lists, truncate long strings, cap depth."""
    if depth > 5:
        return "…"
    if isinstance(obj, dict):
        return {k: _trim(v, depth + 1, max_list, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        head = [_trim(v, depth + 1, max_list, max_str) for v in obj[:max_list]]
        if len(obj) > max_list:
            head.append(f"… {len(obj) - max_list} more")
        return head
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "…"
    return obj


def _frame_summary(df) -> dict:
    """For DataFrame endpoints: keep the shape, not 364 rows of JSON."""
    if df is None or len(df) == 0:
        return {"rows": 0}
    return {
        "rows": int(len(df)),
        "first": str(df.index.min()),
        "last": str(df.index.max()),
        "columns": list(df.columns),
        "tail": [
            {"time": str(i), **{k: (None if v is None else round(float(v), 4) if isinstance(v, (int, float)) else v)
                                for k, v in row.items()}}
            for i, row in df.tail(2).iterrows()
        ],
    }


def main() -> None:
    if not settings.has_cmc:
        raise SystemExit("CMC_PRO_API_KEY not configured — cannot capture evidence.")
    cmc = CMCClient()
    OUT.mkdir(parents=True, exist_ok=True)
    captured = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []

    for slug, endpoint, why, fn in CASES:
        entry = {
            "capturedAt": captured,
            "endpoint": endpoint,
            "why": why,
            "response": None,
            "error": None,
        }
        try:
            got = fn(cmc)
            if hasattr(got, "columns"):        # pandas DataFrame (history)
                entry["response"] = _frame_summary(got)
            else:
                entry["response"] = _trim(got)
            ok = True
        except CMCError as e:
            entry["error"] = str(e)
            ok = False
        (OUT / f"{slug}.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
        rows.append((slug, endpoint, "ok" if ok else f"error: {entry['error']}", why))
        print(f"  {'ok  ' if ok else 'FAIL'} {slug}")

    index = [
        "# CMC API evidence pack",
        "",
        f"Real responses captured from `pro-api.coinmarketcap.com` on **{captured}**.",
        "Payloads are trimmed (short lists, long strings cut) — the shapes and fields are unmodified.",
        "",
        "| File | Endpoint | Result | What it powers |",
        "| --- | --- | --- | --- |",
    ]
    for slug, endpoint, status, why in rows:
        index.append(f"| [`{slug}.json`]({slug}.json) | `{endpoint}` | {status} | {why} |")
    index.append("")
    (OUT / "README.md").write_text("\n".join(index), encoding="utf-8")
    print(f"\nwrote {OUT / 'README.md'} ({len(rows)} endpoints)")


if __name__ == "__main__":
    main()
