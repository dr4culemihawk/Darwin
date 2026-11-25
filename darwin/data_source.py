"""Market data loader.

Uses the real CoinMarketCap API when a key is configured; otherwise falls back
to a deterministic synthetic generator so the engine is always testable without
spending API credits. Synthetic data is seeded per-symbol => reproducible.
"""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
import pandas as pd

from .cmc.client import CMCClient, CMCError
from .config import settings

_TIMEFRAME_TO_CMC = {
    "1d": ("daily", "daily"),
    "1h": ("hourly", "hourly"),
    "1w": ("daily", "weekly"),
}


def _seed_for(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % (2**32)


def synthetic_ohlcv(symbol: str, n: int = 365, timeframe: str = "1d") -> pd.DataFrame:
    """Deterministic geometric-random-walk candles with per-symbol regime shifts."""
    rng = np.random.default_rng(_seed_for(symbol))
    drift = rng.uniform(-0.0003, 0.0009)          # daily drift
    vol = rng.uniform(0.02, 0.06)                  # daily vol
    price = rng.uniform(0.5, 500.0)

    closes = np.empty(n)
    # Inject a couple of regime changes so trend/mean-reversion edges can exist.
    regime = rng.uniform(-1, 1, size=3)
    for i in range(n):
        seg = min(i // max(1, n // 3), 2)
        step = drift * (1 + regime[seg]) + vol * rng.standard_normal()
        price *= float(np.exp(step))
        closes[i] = price

    freq = {"1d": "D", "1h": "h", "1w": "W"}.get(timeframe, "D")
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=n, freq=freq)

    opens = np.empty(n)
    opens[0] = closes[0] * (1 - vol * 0.5)
    opens[1:] = closes[:-1]
    intrabar = np.abs(rng.standard_normal(n)) * vol * 0.5
    highs = np.maximum(opens, closes) * (1 + intrabar)
    lows = np.minimum(opens, closes) * (1 - intrabar)
    volume = rng.uniform(1e6, 1e8, size=n)

    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volume},
        index=idx,
    )


# Which source served each symbol on the last load_market_data() call
# (surfaced in reports / the dashboard so the data's origin is visible).
LAST_PROVENANCE: dict[str, str] = {}

SOURCES = ("auto", "cmc_ohlcv", "cmc_quotes", "binance", "synthetic")
# A daily-candle source that ends more than this many days ago is stale: an old
# cache entry (or a dead feed) must never masquerade as "today's market".
MAX_STALENESS_DAYS = 3
# Why a source was skipped on the last load — surfaced for transparency.
LAST_NOTES: dict[str, str] = {}


def _is_stale(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return True
    last = pd.Timestamp(df.index.max())
    if last.tzinfo is None:
        last = last.tz_localize("UTC")
    return last < pd.Timestamp.utcnow() - pd.Timedelta(days=MAX_STALENESS_DAYS)



def load_market_data(
    symbols: list[str],
    count: int = 365,
    timeframe: str = "1d",
    force_synthetic: bool = False,
    source: str = "auto",
) -> dict[str, pd.DataFrame]:
    """Return {symbol -> OHLCV DataFrame}.

    `source="auto"` preference order:
      1. CMC /v2/cryptocurrency/ohlcv/historical   (true OHLCV; not on the Startup tier)
      2. CMC /v2/cryptocurrency/quotes/historical  (daily candles; Startup tier, 12 months)
      3. Binance public klines                     (non-CMC fallback)
      4. deterministic synthetic                   (offline / tests)
    Pin a specific `source` (e.g. "cmc_quotes") to force fresh CMC-only data.
    """
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    LAST_PROVENANCE.clear()
    if force_synthetic or source == "synthetic":
        LAST_PROVENANCE.update({s: "synthetic" for s in symbols})
        return {s: synthetic_ohlcv(s, count, timeframe) for s in symbols}

    from .binance import binance_klines

    cmc = None
    if settings.has_cmc:
        try:
            cmc = CMCClient()
        except CMCError:
            cmc = None
    time_period, interval = _TIMEFRAME_TO_CMC.get(timeframe, ("daily", "daily"))

    def try_cmc_ohlcv(s):
        return cmc.ohlcv_historical(s, count=count, time_period=time_period, interval=interval)

    def try_cmc_quotes(s):
        if timeframe != "1d":
            return None  # Startup tier: intraday quote history is capped at 1 month
        return cmc.quotes_historical_daily(s, days=min(count, 364))

    def try_binance(s):
        return binance_klines(s, count=count, timeframe=timeframe)

    chain = {
        "auto": [("cmc_ohlcv", try_cmc_ohlcv), ("cmc_quotes", try_cmc_quotes), ("binance", try_binance)],
        "cmc_ohlcv": [("cmc_ohlcv", try_cmc_ohlcv)],
        "cmc_quotes": [("cmc_quotes", try_cmc_quotes)],
        "binance": [("binance", try_binance)],
    }[source]

    out: dict[str, pd.DataFrame] = {}
    LAST_NOTES.clear()
    for s in symbols:
        df, used = None, "synthetic"
        for name, fn in chain:
            if name.startswith("cmc") and cmc is None:
                continue
            try:
                got = fn(s)
            except Exception as e:                       # noqa: BLE001 - try the next source
                LAST_NOTES[s] = f"{name} failed: {type(e).__name__}"
                got = None
            if got is not None and not got.empty and _is_stale(got):
                # An old cache entry must not pass as live data — skip it loudly.
                LAST_NOTES[s] = (
                    f"{name} skipped: last bar {pd.Timestamp(got.index.max()).date()} "
                    f"is older than {MAX_STALENESS_DAYS}d"
                )
                got = None
            if got is not None and not got.empty:
                df, used = got, name
                break
        out[s] = df if df is not None else synthetic_ohlcv(s, count, timeframe)
        LAST_PROVENANCE[s] = used
    return out


def load_fear_greed() -> pd.DataFrame | None:
    """CMC's proprietary 0-100 sentiment index as a time series, or None.

    The endpoint caps `limit` at 500 (it previously asked for 1000, got a 400, and
    silently fell back to synthetic data). Failures are now logged, not swallowed.
    """
    if not settings.has_cmc:
        return None
    try:
        return CMCClient().fear_greed_historical(limit=500)
    except CMCError as e:
        warnings.warn(f"CMC Fear & Greed unavailable, using synthetic fallback: {e}")
        return None


# Origin of each market signal on the last load_signals() call ("cmc" / "synthetic").
SIGNAL_PROVENANCE: dict[str, str] = {}


def synthetic_fgi(n: int = 500, timeframe: str = "1d") -> pd.Series:
    """Deterministic mean-reverting Fear & Greed proxy (0-100) for offline demos."""
    rng = np.random.default_rng(99)
    vals = np.empty(n)
    x = 50.0
    for i in range(n):
        x = float(np.clip(x + rng.normal(0, 7) + (50.0 - x) * 0.05, 5, 95))
        vals[i] = x
    freq = {"1d": "D", "1h": "h", "1w": "W"}.get(timeframe, "D")
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=n, freq=freq)
    return pd.Series(vals, index=idx, name="fgi")


def derive_market_signals(data: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """Compute market-wide regime signals from CMC OHLCV (no extra API calls):

    - `mom`     : cross-sectional momentum — mean trailing 30-bar % return across
                  the universe (positive = broad uptrend).
    - `breadth` : % of the universe trading above its own 50-bar SMA (market health).

    Both are historical series, so strategies can gate entries/exits on regime and
    the backtester scores them like any other signal.
    """
    frames = [df for df in data.values() if not df.empty]
    if not frames:
        return {}
    idx = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in frames])))
    closes = pd.DataFrame(
        {s: df["close"].reindex(idx).ffill() for s, df in data.items() if not df.empty}
    )
    mom = (closes.pct_change(30) * 100.0).mean(axis=1)
    sma = closes.rolling(50, min_periods=10).mean()
    breadth = (closes > sma).mean(axis=1) * 100.0
    return {"mom": mom.rename("mom").fillna(0.0), "breadth": breadth.rename("breadth").fillna(50.0)}


def load_cmc_regime_signals() -> dict[str, pd.Series]:
    """NEW (Round 2): cross-market regime signals from CMC global metrics + RWA.

    - `btc_dom`   : BTC dominance, % of total crypto market cap
                    (/v1/global-metrics/quotes/historical).
    - `dom_trend` : 30-day change in BTC dominance, percentage points. Rising =
                    capital hiding in BTC (alt risk-off); falling = alt rotation.
    - `gold_rs`   : crypto-vs-gold relative strength: 30-day % return of total
                    crypto market cap minus 30-day % return of tokenized gold
                    (/v5/real-world-assets/quotes/historical, symbol=GOLD).
                    Positive = crypto outperforming the classic safe haven (risk-on).

    Series are stamped 00:00 UTC and aligned to bars as-of (no look-ahead).
    Startup tier: last 12 months only, so earlier bars see NaN (= condition False).
    """
    if not settings.has_cmc:
        return {}
    try:
        cmc = CMCClient()
    except CMCError:
        return {}
    # Lazy import: darwin.regime imports this module for its synthetic fallback.
    from .regime import regime_series

    gm, gold = pd.DataFrame(), pd.DataFrame()
    try:
        gm = cmc.global_metrics_historical()
    except CMCError:
        pass
    try:
        gold = cmc.rwa_quotes_historical("GOLD")
    except CMCError:
        pass
    return regime_series(gm, gold)


def synthetic_regime_signals(n: int = 500, timeframe: str = "1d") -> dict[str, pd.Series]:
    """Deterministic stand-ins so offline demos/tests exercise every signal."""
    rng = np.random.default_rng(7)
    freq = {"1d": "D", "1h": "h", "1w": "W"}.get(timeframe, "D")
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=n, freq=freq)
    dom = pd.Series(55 + np.cumsum(rng.normal(0, 0.25, n)).clip(-8, 8), index=idx)
    rs = pd.Series(np.cumsum(rng.normal(0, 2.0, n)).clip(-40, 40), index=idx)
    return {"btc_dom": dom, "dom_trend": dom.diff(30).fillna(0.0), "gold_rs": rs}


def load_signals(count: int = 500, timeframe: str = "1d", force_synthetic: bool = False) -> dict[str, pd.Series]:
    """Market-wide signals usable by strategy conditions: `fgi` (CMC Fear & Greed)
    plus the Round 2 CMC regime signals (`btc_dom`, `dom_trend`, `gold_rs`).
    Falls back to deterministic synthetic series offline."""
    SIGNAL_PROVENANCE.clear()
    if force_synthetic or not settings.has_cmc:
        out = {"fgi": synthetic_fgi(count, timeframe), **synthetic_regime_signals(count, timeframe)}
        SIGNAL_PROVENANCE.update({k: "synthetic" for k in out})
        return out
    out: dict[str, pd.Series] = {}
    fg = load_fear_greed()
    if fg is not None and "value" in fg.columns and not fg.empty:
        out["fgi"] = fg["value"].astype(float)
        SIGNAL_PROVENANCE["fgi"] = "cmc"
    else:
        out["fgi"] = synthetic_fgi(count, timeframe)
        SIGNAL_PROVENANCE["fgi"] = "synthetic"
    regime = load_cmc_regime_signals()
    out.update(regime)
    SIGNAL_PROVENANCE.update({k: "cmc" for k in regime})
    return out
