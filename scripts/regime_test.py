"""Round 2 tests — regime radar, RWA snapshot, today's champion signal.

Runs fully offline on deterministic synthetic data. Run:
    python -m scripts.regime_test
"""
from __future__ import annotations

import math

import pandas as pd

from darwin.data_source import (
    _is_stale,
    derive_market_signals,
    load_market_data,
    load_signals,
    synthetic_regime_signals,
)
from darwin.regime import (
    DOM_TREND_BAND,
    champion_signal,
    classify_regime,
    explain_condition,
    regime_series,
    regime_snapshot,
    rwa_snapshot,
)
from darwin.strategy.spec import StrategySpec

UNIVERSE = ["BTC", "ETH", "BNB"]


def _spec(entry: dict, exit_: dict, indicators: list[dict] | None = None) -> StrategySpec:
    return StrategySpec.from_dict(
        {
            "name": "regime test",
            "universe": UNIVERSE,
            "timeframe": "1d",
            "indicators": indicators
            or [{"id": "ema_f", "type": "EMA", "period": 12}, {"id": "ema_s", "type": "EMA", "period": 30}],
            "entry": entry,
            "exit": exit_,
            "risk": {"max_position_pct": 0.2, "max_open_positions": 3, "stop_loss_pct": 0.08,
                     "take_profit_pct": 0.25, "max_drawdown_pct": 0.3, "trailing_stop_pct": 0.0},
            "sizing": {"type": "equal_weight"},
            "rationale": "test",
        }
    )


def test_regime_series_math() -> None:
    """btc_dom / dom_trend / gold_rs are computed exactly as specified."""
    idx = pd.date_range("2026-01-01", periods=60, freq="D", tz="UTC")
    dom = [50.0 + i * 0.1 for i in range(60)]
    mcap = [1e12 * (1.01 ** i) for i in range(60)]
    gold = [2000.0 * (1.005 ** i) for i in range(60)]
    gm = pd.DataFrame(
        {"btc_dominance": dom, "eth_dominance": [10.0] * 60,
         "total_market_cap": mcap, "altcoin_market_cap": [1e11] * 60},
        index=idx,
    )
    gold_df = pd.DataFrame({"price": gold}, index=idx)

    s = regime_series(gm, gold_df)
    assert set(s) == {"btc_dom", "dom_trend", "gold_rs"}, s.keys()
    assert s["btc_dom"].iloc[-1] == dom[-1]
    expected_trend = dom[-1] - dom[-1 - 30]
    assert math.isclose(s["dom_trend"].iloc[-1], expected_trend, rel_tol=1e-9)

    crypto_ret = (mcap[-1] / mcap[-1 - 30] - 1) * 100
    gold_ret = (gold[-1] / gold[-1 - 30] - 1) * 100
    assert math.isclose(s["gold_rs"].iloc[-1], crypto_ret - gold_ret, rel_tol=1e-6), (
        s["gold_rs"].iloc[-1], crypto_ret - gold_ret
    )
    # 1%/day crypto vs 0.5%/day gold over 30 bars => crypto ahead.
    assert s["gold_rs"].iloc[-1] > 0
    print(f"  regime_series: dom={s['btc_dom'].iloc[-1]:.1f} trend={expected_trend:+.2f}pp "
          f"gold_rs={s['gold_rs'].iloc[-1]:+.2f}%")

    # Missing inputs degrade gracefully instead of raising: no global metrics means
    # nothing at all, but a missing gold series still yields the dominance signals.
    assert regime_series(pd.DataFrame(), gold_df) == {}
    no_gold = regime_series(gm, pd.DataFrame())
    assert "gold_rs" not in no_gold and "btc_dom" in no_gold and "dom_trend" in no_gold
    print("  regime_series: empty/missing inputs handled")


def test_classify_regime() -> None:
    """All four quadrants plus the neutral band produce the documented labels."""
    up, down = DOM_TREND_BAND + 2, -(DOM_TREND_BAND + 2)
    cases = [
        (up, -5.0, "risk-off"),
        (down, 5.0, "risk-on"),
        (up, 5.0, "neutral"),
        (down, -5.0, "neutral"),
        (0.0, 0.0, "neutral"),
    ]
    for trend, rs, tone in cases:
        got = classify_regime(trend, rs)
        assert got["tone"] == tone, (trend, rs, got)
        assert got["label"] and got["note"]
    # Unknown inputs must not crash or silently claim risk-on.
    assert classify_regime(None, None)["tone"] == "neutral"
    print(f"  classify_regime: {len(cases)} quadrants + None inputs OK")


def test_snapshot_offline() -> None:
    snap = regime_snapshot(force_synthetic=True)
    assert snap["source"] == "synthetic", snap["source"]
    for k in ("asOf", "label", "tone", "note", "metrics", "history", "components", "provenance"):
        assert k in snap, k
    assert snap["tone"] in {"risk-on", "risk-off", "neutral"}
    assert len(snap["history"]) > 0
    print(f"  regime_snapshot(synthetic): '{snap['label']}' · {len(snap['history'])} history points")

    rwa = rwa_snapshot(force_synthetic=True)
    assert rwa["source"] == "synthetic"
    for k in ("asset", "issuers", "concentration", "leaderboard"):
        assert k in rwa, k
    print("  rwa_snapshot(synthetic): shape OK")


def test_champion_signal() -> None:
    data = load_market_data(UNIVERSE, count=300, force_synthetic=True)
    signals = load_signals(count=300, force_synthetic=True)
    signals.update(derive_market_signals(data))
    sig = synthetic_regime_signals(300)
    signals.update(sig)

    # A condition that is always true -> every symbol must want to enter.
    always = _spec({"all": [{"left": "gold_rs", "op": ">", "right": -1e9}]},
                   {"any": [{"left": "gold_rs", "op": ">", "right": 1e9}]})
    out = champion_signal(always, data, signals)
    assert {a["symbol"] for a in out["actions"]} == set(UNIVERSE)
    assert all(a["action"] == "enter" for a in out["actions"]), [a["action"] for a in out["actions"]]
    assert out["summary"].startswith("entry fires on")
    for a in out["actions"]:
        assert a["entry"] and a["exit"], a
        assert a["entry"][0]["result"] is True
        assert a["exit"][0]["result"] is False
        assert a["asOf"] == str(pd.Timestamp(data[a["symbol"]].index[-1]).date())
    print(f"  champion_signal: always-true entry -> {len(out['actions'])} ENTER")

    # Never true -> flat, and the operands are still reported.
    never = _spec({"all": [{"left": "gold_rs", "op": ">", "right": 1e9}]},
                  {"any": [{"left": "gold_rs", "op": "<", "right": -1e9}]})
    out2 = champion_signal(never, data, signals)
    assert all(a["action"] == "flat" for a in out2["actions"])
    assert out2["summary"].startswith("no entry fires")
    assert out2["actions"][0]["entry"][0]["leftValue"] is not None
    print("  champion_signal: never-true entry -> FLAT with operands")

    # A signal that is absent from the data is reported as unknown, not as False.
    missing = _spec({"all": [{"left": "nonexistent_sig", "op": ">", "right": 1}]},
                    {"any": [{"left": "close", "op": "<", "right": 0}]})
    out3 = champion_signal(missing, data, signals)
    assert all(a["action"] == "unknown" for a in out3["actions"]), out3["summary"]
    assert out3["actions"][0]["entry"][0]["result"] is None
    print("  champion_signal: unavailable series -> UNKNOWN (not silently False)")

    # explain_condition mirrors eval_condition for a real indicator comparison.
    frame = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
    leaves = explain_condition({"all": [{"left": "close", "op": ">", "right": 5}]}, frame)
    assert leaves[0]["result"] is True and leaves[0]["rightValue"] == 5.0
    print("  explain_condition: leaf operands + truth OK")


def test_freshness_guard() -> None:
    """A stale candle series must be rejected rather than passed off as live."""
    now = pd.Timestamp.now(tz="UTC")
    fresh = pd.DataFrame({"close": [1.0]}, index=[now - pd.Timedelta(days=1)])
    stale = pd.DataFrame({"close": [1.0]}, index=[now - pd.Timedelta(days=200)])
    assert not _is_stale(fresh)
    assert _is_stale(stale)
    assert _is_stale(pd.DataFrame())
    print("  freshness guard: fresh accepted, 200d-old rejected, empty rejected")


def main() -> None:
    print("Round 2 tests (offline):")
    test_regime_series_math()
    test_classify_regime()
    test_snapshot_offline()
    test_champion_signal()
    test_freshness_guard()
    print("\nOK — regime / RWA / today's-signal pass.")


if __name__ == "__main__":
    main()
