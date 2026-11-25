"""Regime Radar & today's champion signal — NEW for "Build with CMC" Round 2.

Two capabilities live here, both driven by CoinMarketCap endpoints that Darwin
only started using in this round (global metrics, Real-World Assets, CMC100):

1. `regime_snapshot()` — a cross-market radar. BTC dominance and its 30-day
   trend, ETH dominance, total/altcoin market cap, the CMC100 index level, and
   tokenized gold as the classic safe haven (crypto-vs-gold relative strength).
   Strategies can gate on three of these as first-class spec signals:
   `btc_dom`, `dom_trend`, `gold_rs`.

2. `champion_signal()` — evaluate the locked champion's OWN condition tree on the
   latest closed bar, with a per-condition breakdown, so anyone can see what the
   strategy would do at the next open. It calls the backtester's `eval_condition`,
   so the answer can never drift from what a backtest would say.

3. `rwa_snapshot()` — the tokenized-gold issuer breakdown (PAXG vs XAUt vs ...)
   plus the broader RWA leaderboard by 24h tokenized volume.

Everything degrades to deterministic synthetic values offline, and every payload
carries `source` so the dashboard can show where a number came from.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .cmc.client import CMCClient, CMCError
from .config import settings
from .strategy.backtest import align_signal, eval_condition
from .strategy.indicators import compute_all
from .strategy.spec import StrategySpec

# 30-day lookbacks match the spec signals (dom_trend / gold_rs are 30-bar changes).
LOOKBACK = 30
# Inside +-DOM_TREND_BAND percentage points, dominance is treated as steady.
DOM_TREND_BAND = 1.0


# ---------------------------------------------------------------------------
# Pure computations (shared with data_source, so there is one definition)
# ---------------------------------------------------------------------------


def regime_series(gm: pd.DataFrame, gold: pd.DataFrame) -> dict[str, pd.Series]:
    """The canonical Round-2 regime signals, computed from CMC history.

    - `btc_dom`   : BTC dominance (% of total crypto market cap).
    - `dom_trend` : 30-day change in BTC dominance, percentage points.
    - `gold_rs`   : 30-day % return of total crypto market cap MINUS the same for
                    tokenized gold. Positive = crypto outperforming the safe haven.

    Both inputs are the DataFrames returned by CMCClient.global_metrics_historical()
    and CMCClient.rwa_quotes_historical(). Missing inputs yield an empty dict, and
    a missing gold series still returns the two dominance signals.
    """
    out: dict[str, pd.Series] = {}
    if gm is None or gm.empty or "btc_dominance" not in gm.columns:
        return out
    dom = gm["btc_dominance"].astype(float).dropna()
    if dom.empty:
        return out
    out["btc_dom"] = dom.rename("btc_dom")
    out["dom_trend"] = dom.diff(LOOKBACK).rename("dom_trend")
    if gold is not None and not gold.empty and "price" in gold.columns:
        crypto_ret = gm["total_market_cap"].astype(float).pct_change(LOOKBACK) * 100.0
        gold_ret = gold["price"].astype(float).pct_change(LOOKBACK) * 100.0
        rs = (crypto_ret - gold_ret.reindex(crypto_ret.index, method="ffill")).dropna()
        if not rs.empty:
            out["gold_rs"] = rs.rename("gold_rs")
    return out


def classify_regime(dom_trend: float | None, gold_rs: float | None) -> dict[str, str]:
    """Two explicit axes -> one human label. Thresholds are documented, not tuned.

    Dominance axis: BTC dominance rising = capital concentrating in BTC (alts
    risk-off); falling = rotation into alts. Inside +-DOM_TREND_BAND = steady.
    Risk-appetite axis: `gold_rs` > 0 = crypto beating tokenized gold.
    """
    dom_up = dom_trend is not None and dom_trend > DOM_TREND_BAND
    dom_down = dom_trend is not None and dom_trend < -DOM_TREND_BAND
    crypto_bid = gold_rs is not None and gold_rs > 0

    if dom_up and gold_rs is not None and not crypto_bid:
        return {
            "label": "Risk-off — into BTC and gold",
            "tone": "risk-off",
            "note": "Dominance climbing while gold outruns crypto: capital is hiding in the safest assets.",
        }
    if dom_down and crypto_bid:
        return {
            "label": "Risk-on — alts bid",
            "tone": "risk-on",
            "note": "Dominance falling while crypto beats gold: risk appetite is rotating down the cap curve.",
        }
    if dom_up:
        return {
            "label": "BTC-heavy — alts lagging",
            "tone": "neutral",
            "note": "Capital is concentrating in BTC; crypto as a whole is not yet losing to gold.",
        }
    if dom_down:
        return {
            "label": "Alt rotation, but defensive",
            "tone": "neutral",
            "note": "Dominance is falling, yet gold still leads crypto — rotation, not risk appetite.",
        }
    return {
        "label": "Mixed / range-bound",
        "tone": "neutral",
        "note": "Dominance is steady inside the band; no clear cross-market regime.",
    }


def _r(v: Any, digits: int = 4) -> float | None:
    """Rounded float or None (for JSON-safe payloads)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, digits)


def _series_at(s: pd.Series | None, i: int = -1, digits: int = 4) -> float | None:
    if s is None or len(s) < abs(i):
        return None
    try:
        return _r(s.iloc[i], digits)
    except (IndexError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Regime snapshot
# ---------------------------------------------------------------------------


def _cmc():
    if not settings.has_cmc:
        return None
    try:
        return CMCClient()
    except CMCError:
        return None


def _synthetic_regime_snapshot() -> dict[str, Any]:
    """Offline stand-in with the same shape, so the dashboard always renders."""
    from .data_source import synthetic_regime_signals

    sig = synthetic_regime_signals(LOOKBACK + 60)
    dom, trend, rs = sig["btc_dom"], sig["dom_trend"], sig["gold_rs"]
    dom_now, trend_now, rs_now = _series_at(dom, -1, 2), _series_at(trend, -1, 2), _series_at(rs, -1, 2)
    cls = classify_regime(trend_now, rs_now)
    idx = dom.index[-90:]
    return {
        "asOf": str(idx[-1].date()),
        "source": "synthetic",
        "label": cls["label"],
        "tone": cls["tone"],
        "note": cls["note"],
        "metrics": {
            "btcDominance": dom_now,
            "domChange30d": trend_now,
            "ethDominance": None,
            "totalMarketCap": None,
            "marketCapChange30d": None,
            "cmc100": None,
            "cmc100Change24h": None,
            "goldPrice": None,
            "goldChange30d": None,
            "goldRs": rs_now,
        },
        "history": [
            {"date": str(d.date()), "btcDominance": _r(dom.get(d), 2), "goldRs": _r(rs.reindex([d]).iloc[0], 2)}
            for d in idx
        ],
        "components": [],
        "provenance": {"globalMetrics": "synthetic", "rwa": "synthetic", "cmc100": "synthetic"},
    }


def regime_snapshot(force_synthetic: bool = False) -> dict[str, Any]:
    """Cross-market regime radar from CMC global metrics + RWA gold + CMC100.

    Falls back to a deterministic synthetic snapshot when CMC is unavailable, so
    the dashboard and the MCP tool always answer. `source` says which one you got.
    """
    cmc = None if force_synthetic else _cmc()
    if cmc is None:
        return _synthetic_regime_snapshot()

    provenance = {"globalMetrics": "unavailable", "rwa": "unavailable", "cmc100": "unavailable"}
    gm, gold, idx_payload, gold_latest = pd.DataFrame(), pd.DataFrame(), None, {}

    try:
        gm = cmc.global_metrics_historical()
        if not gm.empty:
            provenance["globalMetrics"] = "CoinMarketCap"
    except CMCError:
        pass
    try:
        gold = cmc.rwa_quotes_historical("GOLD")
        if not gold.empty:
            provenance["rwa"] = "CoinMarketCap"
    except CMCError:
        pass
    try:
        idx_payload = cmc.cmc100_latest()
        provenance["cmc100"] = "CoinMarketCap"
    except CMCError:
        pass
    try:
        gold_latest = cmc.rwa_quotes_latest("GOLD")
    except CMCError:
        gold_latest = {}

    if gm.empty and gold.empty and not idx_payload:
        return _synthetic_regime_snapshot()

    series = regime_series(gm, gold)
    dom = series.get("btc_dom")
    trend_now = _series_at(series.get("dom_trend"), -1, 2)
    rs_now = _series_at(series.get("gold_rs"), -1, 2)
    cls = classify_regime(trend_now, rs_now)

    mcap = gm["total_market_cap"].astype(float) if "total_market_cap" in gm.columns else None
    gold_px = gold["price"].astype(float) if "price" in gold.columns else None
    gold_renamed = gold_px.rename("price") if gold_px is not None else None
    gold_ret = _series_at(
        gold_renamed.pct_change(LOOKBACK) * 100.0 if gold_renamed is not None else None, -1, 2
    )
    if gold_px is None:
        quote = (gold_latest.get("quotes") or [{}])[0]
        gold_now = _r(quote.get("average_tokenized_price"), 2)
    else:
        gold_now = _series_at(gold_px, -1, 2)

    gold_mcap = _r(gold_latest.get("tokenized_market_cap"), 0) or _series_at(
        gold.get("market_cap") if "market_cap" in gold.columns else None, -1, 0
    )
    gold_vol = _r(gold_latest.get("tokenized_volume_24h"), 0) or _series_at(
        gold.get("volume_24h") if "volume_24h" in gold.columns else None, -1, 0
    )

    metrics = {
        "btcDominance": _series_at(dom, -1, 2),
        "domChange30d": trend_now,
        "ethDominance": _series_at(
            gm["eth_dominance"].astype(float) if "eth_dominance" in gm.columns else None, -1, 2
        ),
        "totalMarketCap": _series_at(mcap, -1, 0),
        "marketCapChange30d": _series_at(mcap.pct_change(LOOKBACK) * 100.0, -1, 2) if mcap is not None else None,
        "cmc100": _r((idx_payload or {}).get("value"), 2),
        "cmc100Change24h": _r((idx_payload or {}).get("value_24h_percentage_change"), 2),
        "goldPrice": gold_now,
        "goldChange30d": gold_ret,
        "goldRs": rs_now,
        "goldMarketCap": gold_mcap,
        "goldVolume24h": gold_vol,
    }

    as_of = gm.index[-1] if not gm.empty else (gold.index[-1] if not gold.empty else pd.Timestamp.utcnow())
    hist_index = (dom.index if dom is not None else pd.DatetimeIndex([]))[-90:]
    history = []
    for d in hist_index:
        history.append(
            {
                "date": str(pd.Timestamp(d).date()),
                "btcDominance": _r(dom.get(d), 2) if dom is not None else None,
                "goldRs": _r(series["gold_rs"].asof(d), 2) if "gold_rs" in series else None,
            }
        )

    return {
        "asOf": str(pd.Timestamp(as_of).date()),
        "source": "CoinMarketCap",
        "label": cls["label"],
        "tone": cls["tone"],
        "note": cls["note"],
        "metrics": metrics,
        "history": history,
        "components": _components(metrics, provenance),
        "provenance": provenance,
    }


def _components(m: dict[str, Any], provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Judge-readable rows: what each number says about the market."""

    def row(name, value, reading, endpoint, fmt="num", digits=2):
        return {
            "name": name,
            "value": value,
            "reading": reading,
            "endpoint": endpoint,
            "format": fmt,
            "digits": digits,
            "source": provenance.get(_ENDPOINT_KEY[endpoint], "unavailable"),
        }

    dom, trend = m.get("btcDominance"), m.get("domChange30d")
    reading_dom = (
        "steady" if trend is None else
        "climbing — capital concentrating in BTC" if trend > DOM_TREND_BAND else
        "falling — rotation into alts" if trend < -DOM_TREND_BAND else "steady"
    )
    rs = m.get("goldRs")
    reading_rs = (
        "crypto ahead of gold (risk appetite)" if rs is not None and rs > 0
        else "gold ahead of crypto (defensive)" if rs is not None else "unavailable"
    )
    rows = [
        row("BTC dominance", dom, reading_dom, "/v1/global-metrics/quotes/historical", "pct", 2),
        row("Dominance 30d", trend, "percentage points", "/v1/global-metrics/quotes/historical", "pp", 2),
        row("Total market cap", m.get("totalMarketCap"), "30d change "
            + (f"{m['marketCapChange30d']:+.1f}%" if m.get("marketCapChange30d") is not None else "n/a"),
            "/v1/global-metrics/quotes/historical", "usd", 0),
        row("CMC100 index", m.get("cmc100"),
            f"24h {m['cmc100Change24h']:+.2f}%" if m.get("cmc100Change24h") is not None else "n/a",
            "/v3/index/cmc100-latest", "num", 2),
        row("Tokenized gold", m.get("goldPrice"), "30d "
            + (f"{m['goldChange30d']:+.1f}%" if m.get("goldChange30d") is not None else "n/a"),
            "/v5/real-world-assets/quotes/historical", "usd", 2),
        row("Crypto vs gold (30d)", rs, reading_rs, "/v5/real-world-assets/quotes/historical", "pp", 2),
    ]
    return rows


_ENDPOINT_KEY = {
    "/v1/global-metrics/quotes/historical": "globalMetrics",
    "/v3/index/cmc100-latest": "cmc100",
    "/v5/real-world-assets/quotes/historical": "rwa",
}


# ---------------------------------------------------------------------------
# Today's champion signal
# ---------------------------------------------------------------------------


def _ref_name(ref: Any) -> str:
    return f"{ref:g}" if isinstance(ref, (int, float)) and not isinstance(ref, bool) else str(ref)


_OP_TEXT = {
    ">": "is above", "<": "is below", ">=": "is at or above", "<=": "is at or below",
    "cross_above": "crossed above", "cross_below": "crossed below",
}


def _leaves(node: dict[str, Any]):
    if "all" in node:
        for c in node["all"]:
            yield from _leaves(c)
    elif "any" in node:
        for c in node["any"]:
            yield from _leaves(c)
    else:
        yield node


def explain_condition(node: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Every leaf of a condition tree, with its latest operands and truth value.

    `result` is None when the strategy could not be evaluated on the last bar
    because a referenced series had no history yet (e.g. a CMC regime signal
    before the 12-month Startup-tier lookback) — reported honestly rather than
    silently coerced to False.
    """
    out = []
    for leaf in _leaves(node):
        left_val = _resolve_last(leaf["left"], frame)
        right_val = _resolve_last(leaf["right"], frame)
        truth_series = eval_condition(leaf, frame)
        if left_val is None or right_val is None or (isinstance(left_val, float) and np.isnan(left_val)):
            result = None
        elif len(truth_series):
            result = bool(truth_series.iloc[-1])
        else:
            result = None
        out.append(
            {
                "text": f"{_ref_name(leaf['left'])} {_OP_TEXT.get(leaf['op'], leaf['op'])} {_ref_name(leaf['right'])}",
                "left": _ref_name(leaf["left"]),
                "op": leaf["op"],
                "right": _ref_name(leaf["right"]),
                "leftValue": _r(left_val, 2),
                "rightValue": _r(right_val, 2),
                "result": result,
            }
        )
    return out


def _resolve_last(ref: Any, frame: pd.DataFrame) -> float | None:
    if isinstance(ref, (int, float)) and not isinstance(ref, bool):
        return float(ref)
    if isinstance(ref, str) and ref in frame.columns and len(frame):
        v = frame[ref].iloc[-1]
        return None if pd.isna(v) else float(v)
    return None


def _combine(results: list[bool | None], mode: str) -> bool | None:
    known = [r for r in results if r is not None]
    if not known:
        return None
    return all(known) if mode == "all" else any(known)


def champion_signal(
    spec: StrategySpec,
    data: dict[str, pd.DataFrame],
    signals: dict[str, pd.Series] | None = None,
) -> dict[str, Any]:
    """What the champion's rules say at the latest close — per symbol.

    Mirrors the backtester's convention exactly: conditions are evaluated on the
    close of the last bar and any resulting order executes at the NEXT open. So
    `action="enter"` means an entry would fire at the next open.
    """
    signals = signals or {}
    per_symbol = []
    for sym in spec.universe:
        df = data.get(sym)
        if df is None or df.empty:
            per_symbol.append({"symbol": sym, "action": "no_data", "asOf": None, "entry": [], "exit": []})
            continue
        df = df.sort_index()
        frame = df.copy()
        ind = compute_all(spec.indicators, df)
        for col in ind.columns:
            frame[col] = ind[col]
        for name, series in signals.items():
            frame[name] = align_signal(series, df.index)

        entry_leaves = explain_condition(spec.entry, frame)
        exit_leaves = explain_condition(spec.exit, frame)
        entry_mode = "all" if "all" in spec.entry else "any"
        exit_mode = "all" if "all" in spec.exit else "any"
        entry_hit = _combine([l["result"] for l in entry_leaves], entry_mode)
        exit_hit = _combine([l["result"] for l in exit_leaves], exit_mode)

        if entry_hit:
            action, reason = "enter", "entry rules fire on the latest close → buy at the next open"
        elif exit_hit:
            action, reason = "exit", "exit rules fire on the latest close → close at the next open"
        elif entry_hit is None:
            action, reason = "unknown", "not enough history for a required signal"
        else:
            action, reason = "flat", "no rule fires — stay out / hold nothing"

        per_symbol.append(
            {
                "symbol": sym,
                "action": action,
                "reason": reason,
                "asOf": str(pd.Timestamp(df.index[-1]).date()),
                "lastClose": _r(df["close"].iloc[-1], 2),
                "entry": entry_leaves,
                "exit": exit_leaves,
            }
        )

    firing = [p["symbol"] for p in per_symbol if p["action"] == "enter"]
    return {
        "champion": spec.name,
        "fingerprint": spec.fingerprint(),
        "asOf": per_symbol[0]["asOf"] if per_symbol else None,
        "signalSources": sorted(signals.keys()),
        "actions": per_symbol,
        "summary": (
            f"entry fires on {', '.join(firing)}" if firing
            else "no entry fires today — the champion stays flat"
        ),
    }


# ---------------------------------------------------------------------------
# RWA snapshot (tokenized gold issuers + RWA leaderboard)
# ---------------------------------------------------------------------------


def _synthetic_rwa() -> dict[str, Any]:
    return {
        "source": "synthetic",
        "asOf": str(pd.Timestamp.utcnow().date()),
        "asset": {
            "symbol": "GOLD", "name": "Gold", "assetType": "commodity",
            "price": None, "marketCap": None, "volume24h": None, "change30d": None,
        },
        "issuers": [],
        "concentration": None,
        "leaderboard": [],
    }


def rwa_snapshot(symbol: str = "GOLD", force_synthetic: bool = False, top: int = 8) -> dict[str, Any]:
    """Tokenized-gold issuer breakdown + RWA leaderboard by tokenized volume.

    Gold is the cleanest read on *real* risk appetite: when tokenized gold
    absorbs volume while crypto doesn't, the market is defensive. Endpoints:
    /v5/real-world-assets/quotes/{latest,historical} and /assets/list.
    """
    cmc = None if force_synthetic else _cmc()
    if cmc is None:
        return _synthetic_rwa()

    latest, hist, board = {}, pd.DataFrame(), []
    try:
        latest = cmc.rwa_quotes_latest(symbol)
    except CMCError:
        pass
    try:
        hist = cmc.rwa_quotes_historical(symbol)
    except CMCError:
        pass
    try:
        board = cmc.rwa_assets_list(limit=top)
    except CMCError:
        board = []

    if not latest and hist.empty and not board:
        return _synthetic_rwa()

    tokens = latest.get("tokens") or []
    issuer_rows = []
    for t in tokens:
        issuer_rows.append(
            {
                "symbol": t.get("symbol"),
                "name": t.get("name"),
                "issuer": t.get("issuer_name"),
                "price": _r(t.get("price"), 2),
                "marketCap": _r(t.get("market_cap"), 0),
                "volume24h": _r(t.get("volume_24h"), 0),
            }
        )
    issuer_rows.sort(key=lambda r: (r["marketCap"] or 0), reverse=True)
    total_cap = sum(r["marketCap"] or 0 for r in issuer_rows)
    for r in issuer_rows:
        r["share"] = _r((r["marketCap"] or 0) / total_cap, 4) if total_cap else None

    quote = (latest.get("quotes") or [{}])[0]
    change_30d = None
    if not hist.empty and "price" in hist.columns and len(hist) > LOOKBACK:
        change_30d = _series_at(hist["price"].astype(float).pct_change(LOOKBACK) * 100.0, -1, 2)

    leaderboard = [
        {
            "name": a.get("name"),
            "symbol": a.get("symbol"),
            "assetType": a.get("asset_type"),
            "marketCap": _r(a.get("tokenized_market_cap"), 0),
            "volume24h": _r(a.get("tokenized_volume_24h"), 0),
            "price": _r(a.get("average_tokenized_price"), 2),
        }
        for a in board
    ]

    return {
        "source": "CoinMarketCap",
        "asOf": str(pd.Timestamp(latest.get("last_updated") or pd.Timestamp.utcnow()).date()),
        "asset": {
            "symbol": latest.get("symbol", symbol),
            "name": latest.get("name"),
            "assetType": latest.get("asset_type"),
            "price": _r(quote.get("average_tokenized_price") or latest.get("average_tokenized_price"), 2),
            "marketCap": _r(latest.get("tokenized_market_cap"), 0),
            "volume24h": _r(latest.get("tokenized_volume_24h"), 0),
            "change30d": change_30d,
        },
        "issuers": issuer_rows,
        "concentration": issuer_rows[0]["share"] if issuer_rows else None,
        "leaderboard": leaderboard,
    }
