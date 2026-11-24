"""Thin CoinMarketCap Pro API client.

Endpoints used (verified against CMC Pro docs):
  * /v2/cryptocurrency/ohlcv/historical  -> backtest candles (paid tier)
  * /v2/cryptocurrency/quotes/latest      -> live price (all tiers)
  * /v3/fear-and-greed/latest|historical  -> CMC's proprietary sentiment signal
                                             (ALL tiers, incl. free)
  * /v1/cryptocurrency/trending/gainers-losers -> momentum signal (Startup+)

New for "Build with CMC" Round 2 (see docs/CMC_INTEGRATION.md):
  * /v1/global-metrics/quotes/latest|historical -> BTC dominance + altcoin share regime
  * /v5/real-world-assets/quotes/latest|historical -> tokenized gold (crypto-vs-gold
                                                      risk appetite) + issuer breakdown
  * /v5/real-world-assets/assets/list           -> RWA screener by asset type
  * /v5/real-world-assets/issuers/list          -> RWA issuer directory
  * /v3/index/cmc100-latest                     -> CMC100 index level for the regime radar
  * /v1/key/info                                -> plan/credit usage shown in the evidence pack

Plan note: on the Startup tier, global-metrics and RWA history are capped at the
last 12 months (error 1014 beyond that), so those clients clamp `time_start`.

Responses are cached to data/cache/ so repeated backtests don't re-bill credits.
Auth header for REST is X-CMC_PRO_API_KEY (underscores). Note the MCP server uses
a DIFFERENT header, X-CMC-MCP-API-KEY (hyphens) â€” not used here.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from ..config import DATA_DIR, settings

BASE_URL = "https://pro-api.coinmarketcap.com"
# Startup-tier lookback for global-metrics + RWA history (observed, see feedback doc).
HISTORY_LOOKBACK_DAYS = 364


def _lookback_start(days: int = HISTORY_LOOKBACK_DAYS) -> str:
    """ISO date `days` ago (UTC), rounded to the day so the cache key is stable."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


class CMCError(RuntimeError):
    pass


class CMCClient:
    def __init__(self, api_key: str | None = None, cache_dir: Path = DATA_DIR):
        self.api_key = api_key or settings.cmc_api_key
        if not self.api_key:
            raise CMCError("no CMC_PRO_API_KEY configured")
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update(
            {"X-CMC_PRO_API_KEY": self.api_key, "Accept": "application/json"}
        )

    # ---- low-level ---------------------------------------------------------

    def _get(self, path: str, params: dict, cache_ttl: float | None = None) -> dict:
        key = hashlib.sha256(f"{path}?{json.dumps(params, sort_keys=True)}".encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"cmc_{key}.json"
        if cache_file.exists():
            if cache_ttl is None or (time.time() - cache_file.stat().st_mtime) < cache_ttl:
                return json.loads(cache_file.read_text())

        resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        try:
            payload = resp.json()
        except ValueError:
            raise CMCError(f"non-JSON response ({resp.status_code}) from {path}")
        status = payload.get("status", {})
        ec = status.get("error_code")
        # CMC returns error_code 0 (or the string "0") on success; only non-zero is an error.
        if ec and str(ec) != "0":
            raise CMCError(f"CMC error {ec}: {status.get('error_message')}")
        if resp.status_code != 200:
            raise CMCError(f"HTTP {resp.status_code} from {path}")
        cache_file.write_text(json.dumps(payload))
        return payload

    # ---- historical OHLCV --------------------------------------------------

    def ohlcv_historical(
        self,
        symbol: str,
        count: int = 365,
        time_period: str = "daily",
        interval: str = "daily",
        convert: str = "USD",
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame indexed by candle close time (UTC)."""
        payload = self._get(
            "/v2/cryptocurrency/ohlcv/historical",
            {
                "symbol": symbol,
                "count": count,
                "time_period": time_period,
                "interval": interval,
                "convert": convert,
            },
        )
        data = payload["data"]
        # v2 keyed-by-symbol may return a list; normalize to the first match.
        if isinstance(data, dict) and symbol in data:
            data = data[symbol]
        if isinstance(data, list):
            data = data[0]
        rows = []
        for q in data.get("quotes", []):
            cell = q["quote"][convert]
            rows.append(
                {
                    "time": pd.to_datetime(q.get("time_close") or cell.get("timestamp")),
                    "open": cell["open"],
                    "high": cell["high"],
                    "low": cell["low"],
                    "close": cell["close"],
                    "volume": cell.get("volume", 0.0) or 0.0,
                }
            )
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        return df.set_index("time").sort_index()

    # ---- live quotes -------------------------------------------------------

    def quotes_latest(self, symbols: list[str], convert: str = "USD") -> dict:
        payload = self._get(
            "/v2/cryptocurrency/quotes/latest",
            {"symbol": ",".join(symbols), "convert": convert},
            cache_ttl=60,
        )
        out = {}
        for sym, entries in payload["data"].items():
            entry = entries[0] if isinstance(entries, list) else entries
            out[sym] = entry["quote"][convert]
        return out

    # ---- CMC proprietary sentiment signal ----------------------------------

    def fear_greed_latest(self) -> dict:
        payload = self._get("/v3/fear-and-greed/latest", {}, cache_ttl=600)
        return payload["data"]

    def fear_greed_historical(self, limit: int = 500) -> pd.DataFrame:
        payload = self._get("/v3/fear-and-greed/historical", {"limit": limit}, cache_ttl=3600)
        rows = payload.get("data", [])
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        ts_col = "timestamp" if "timestamp" in df.columns else "update_time"
        # CMC returns epoch seconds as a STRING ("1795392000"), newest-first.
        # Coerce to numeric first: to_datetime(unit="s") on strings yields all-NaT,
        # which silently left the series unsorted (oldest value read as "latest").
        epoch = pd.to_numeric(df[ts_col], errors="coerce")
        if epoch.notna().all():
            df["time"] = pd.to_datetime(epoch, unit="s", utc=True)
        else:
            df["time"] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        df = df.dropna(subset=["time"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.set_index("time").sort_index()

    def gainers_losers(self, time_period: str = "24h", limit: int = 20, convert: str = "USD") -> list[dict]:
        payload = self._get(
            "/v1/cryptocurrency/trending/gainers-losers",
            {"time_period": time_period, "limit": limit, "convert": convert},
            cache_ttl=600,
        )
        return payload.get("data", [])

    # ---- daily candles from quotes/historical (NEW, Round 2) ----------------

    def quotes_historical_daily(self, symbol: str, days: int = HISTORY_LOOKBACK_DAYS,
                                convert: str = "USD") -> pd.DataFrame:
        """Daily OHLCV-shaped frame built from /v2/cryptocurrency/quotes/historical.

        The Startup tier does not include /ohlcv/historical, and intraday quote
        history is capped at 1 month, so daily snapshots are the deepest CMC price
        history available. Each row is the 00:00 UTC snapshot: `close` = price,
        `open` = previous snapshot (crypto trades 24/7, so the open IS the prior
        close), and high/low are bounded by open/close (intrabar extremes are not
        available — stops therefore trigger on close-to-close moves only).
        """
        payload = self._get(
            "/v2/cryptocurrency/quotes/historical",
            {"symbol": symbol, "time_start": _lookback_start(days), "interval": "daily",
             "count": days + 1, "convert": convert},
            cache_ttl=6 * 3600,
        )
        data = payload["data"]
        if isinstance(data, dict) and symbol in data:
            data = data[symbol]
        if isinstance(data, list):
            data = data[0] if data else {}
        rows = []
        for q in data.get("quotes", []):
            cell = q["quote"][convert]
            rows.append({
                "time": pd.to_datetime(q["timestamp"], utc=True),
                "close": cell["price"],
                "volume": cell.get("volume_24h") or 0.0,
                "market_cap": cell.get("market_cap"),
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df.groupby("time").last().sort_index()
        df["open"] = df["close"].shift(1).fillna(df["close"])
        df["high"] = df[["open", "close"]].max(axis=1)
        df["low"] = df[["open", "close"]].min(axis=1)
        return df[["open", "high", "low", "close", "volume", "market_cap"]]

    # ---- global market metrics (NEW, Round 2) ------------------------------

    def global_metrics_latest(self, convert: str = "USD") -> dict:
        payload = self._get("/v1/global-metrics/quotes/latest", {"convert": convert}, cache_ttl=300)
        return payload["data"]

    def global_metrics_historical(self, days: int = HISTORY_LOOKBACK_DAYS) -> pd.DataFrame:
        """Daily BTC/ETH dominance, total + altcoin market cap. `count` defaults to
        10 on CMC's side, so we always pass it explicitly."""
        payload = self._get(
            "/v1/global-metrics/quotes/historical",
            {"time_start": _lookback_start(days), "interval": "daily", "count": days + 1},
            cache_ttl=6 * 3600,
        )
        rows = []
        for q in payload["data"].get("quotes", []):
            usd = q.get("quote", {}).get("USD", {})
            rows.append({
                "time": pd.to_datetime(q["timestamp"], utc=True).normalize(),
                "btc_dominance": q.get("btc_dominance"),
                "eth_dominance": q.get("eth_dominance"),
                "total_market_cap": usd.get("total_market_cap"),
                "altcoin_market_cap": usd.get("altcoin_market_cap"),
                "total_volume_24h": usd.get("total_volume_24h"),
            })
        df = pd.DataFrame(rows)
        return df.set_index("time").sort_index() if not df.empty else df

    # ---- CMC100 index (NEW, Round 2) ---------------------------------------

    def cmc100_latest(self) -> dict:
        return self._get("/v3/index/cmc100-latest", {}, cache_ttl=300)["data"]

    # ---- Real-World Assets, v5 (NEW, Round 2) ------------------------------

    def rwa_quotes_latest(self, symbol: str = "GOLD", convert: str = "USD") -> dict:
        """Aggregate tokenized price/cap/volume plus per-issuer `tokens[]`."""
        payload = self._get(
            "/v5/real-world-assets/quotes/latest", {"symbol": symbol, "convert": convert}, cache_ttl=300
        )
        assets = payload["data"].get("rwa_assets", [])
        return assets[0] if assets else {}

    def rwa_quotes_historical(self, symbol: str = "GOLD", days: int = HISTORY_LOOKBACK_DAYS) -> pd.DataFrame:
        payload = self._get(
            "/v5/real-world-assets/quotes/historical",
            {"symbol": symbol, "time_start": _lookback_start(days), "interval": "daily", "count": days + 1},
            cache_ttl=6 * 3600,
        )
        data = payload["data"]
        assets = data.get("rwa_assets") if isinstance(data, dict) else data
        asset = (assets[0] if isinstance(assets, list) and assets else data) or {}
        rows = []
        for q in asset.get("quotes", []):
            rows.append({
                "time": pd.to_datetime(q["timestamp"], utc=True).normalize(),
                "price": q.get("average_tokenized_price"),
                "market_cap": q.get("tokenized_market_cap"),
                "volume_24h": q.get("tokenized_volume_24h"),
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        return df.groupby("time").last().sort_index()

    def rwa_assets_list(self, asset_type: str | None = None, limit: int = 50,
                        sort: str = "tokenized_volume_24h") -> list[dict]:
        params = {"limit": limit, "sort": sort, "sort_dir": "desc"}
        if asset_type:
            params["asset_type"] = asset_type
        payload = self._get("/v5/real-world-assets/assets/list", params, cache_ttl=600)
        return payload["data"].get("rwa_assets", [])

    def rwa_issuers_list(self, limit: int = 100) -> list[dict]:
        payload = self._get("/v5/real-world-assets/issuers/list", {"limit": limit}, cache_ttl=3600)
        return payload["data"].get("issuers", [])

    # ---- account ------------------------------------------------------------

    def key_info(self) -> dict:
        return self._get("/v1/key/info", {}, cache_ttl=60)["data"]
