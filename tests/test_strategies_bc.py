"""Strategies B (H-002) and C (H-003) on the synthetic fixture."""
import hashlib
import math
from pathlib import Path

import pandas as pd
import pytest
import yaml

from pfm import backtest, data
from pfm.strategy_base import Signal

ROOT = Path(__file__).resolve().parent.parent
EVENT_PINS = [(200, 66, "e1e09f31f70b57ce531f0ef12392260e9d559b6177b7e43d46bbe59f2e1e67ed"),
              (900, 275, "9f405ed23a8fc5138ff5a43fece6591d6f36565d8ab0d71c46c3b299f0d0675b")]


@pytest.fixture(scope="module")
def bars():
    return data.synthetic(days=200)


# ---------------------------------------------------------------- B: London fade
def test_b_is_exact_mirror_of_a(bars):
    from strategies.A_asian_breakout.strategy import AsianBreakout
    from strategies.B_london_fade.strategy import LondonFade
    a, b = AsianBreakout().generate_signals(bars), LondonFade().generate_signals(bars)
    assert b and len(a) == len(b)
    for sa, sb in zip(a, b):
        assert sa.time == sb.time and sb.direction == -sa.direction
        ca = (2 * sa.stop + sa.target) / 3                       # A: stop = c − d·r, target = c + 2d·r
        assert math.isclose(abs(sb.stop - ca), abs(ca - sa.stop), rel_tol=1e-9)   # same stop distance
        assert (sb.stop - ca) * sb.direction < 0                 # stop on the far side of the break


def test_breakout_events_unchanged_by_r019():
    """Times, sides, closes and risks are A's audited path: hashes recorded from main at 7c2b194, before `mid` was added."""
    from strategies.A_asian_breakout.strategy import breakout_events
    from strategies.B_london_fade.strategy import LondonFade
    for days, count, digest in EVENT_PINS:
        ev = breakout_events(data.synthetic(days=days), LondonFade.default_params)
        s = "\n".join(f"{e.signal_time.isoformat()},{e.direction},{e.close:.6f},{e.risk:.6f}" for e in ev)
        assert len(ev) == count and hashlib.sha256(s.encode()).hexdigest() == digest


def test_b_target_is_the_range_midpoint_for_both_sides(bars):
    """Rebuilds the range from the bars, independently of breakout_events, including the 23:45 IST bar it wrongly holds (Q-010)."""
    from strategies.B_london_fade.strategy import LondonFade
    sigs = LondonFade().generate_signals(bars)
    assert {s.direction for s in sigs} == {1, -1}
    ist = bars.index.tz_convert("Asia/Kolkata")
    t = pd.Series(ist.time, index=bars.index)
    in_range = ((t >= pd.Timestamp("05:30").time()) & (t < pd.Timestamp("12:30").time())) | (t == pd.Timestamp("23:45").time())
    for s in sigs:
        rng = bars[(ist.date == s.time.tz_convert("Asia/Kolkata").date()) & in_range.values]
        assert s.target == pytest.approx((rng["high"].max() + rng["low"].min()) / 2)
        close = bars.at[s.time - pd.Timedelta(minutes=15), "close"]
        assert (s.target - close) * s.direction > 0              # the target is back towards the range
        assert abs(s.target - close) >= abs(close - s.stop) - 1e-9   # stop is never wider than the midpoint distance


@pytest.mark.xfail(strict=True, reason="Q-010: t_close wraps at midnight, so the 23:45 IST bar joins the 05:30-12:30 IST range. "
                                       "R-019 forbids changing breakout_events. Remove this mark with the fix.")
def test_range_does_not_read_bars_after_the_entry_window(bars):
    from strategies.A_asian_breakout.strategy import breakout_events
    from strategies.B_london_fade.strategy import LondonFade
    late = bars.copy()
    last = late.index.tz_convert("Asia/Kolkata").strftime("%H:%M") == "23:45"     # 7 h after the entry window ends
    late.loc[last, "high"] += 50
    late.loc[last, "low"] -= 50
    k = lambda ev: [(e.signal_time, e.direction, e.close, e.risk, e.mid) for e in ev]
    assert k(breakout_events(late, LondonFade.default_params)) == k(breakout_events(bars, LondonFade.default_params))


def test_b_has_no_rr_and_three_params():
    from strategies.B_london_fade.strategy import LondonFade
    y = yaml.safe_load((ROOT / "strategies/B_london_fade/params.yaml").read_text(encoding="utf-8"))
    assert set(y["default"]) == set(y["ranges"]) == set(LondonFade.default_params) == {"stop_atr", "min_range_atr", "max_range_atr"}
    assert all(LondonFade.default_params[k] == v for k, v in y["default"].items())


@pytest.mark.parametrize("direction, stop, mid", [
    (-1, 2005.0, 1995.0), (-1, 2005.0, 1999.0),                  # short: open at the midpoint, then past it
    (1, 1985.0, 1995.0), (1, 1985.0, 1991.0),                    # long: the same
])
def test_b_entry_bar_opening_at_or_past_the_midpoint_is_rejected(risk_cfg, direction, stop, mid):
    idx = pd.date_range("2026-11-03 08:00", periods=6, freq="15min", tz="UTC")
    b = pd.DataFrame({"open": 1995.0, "high": 1996.0, "low": 1994.0, "close": 1995.0, "spread": 0}, index=idx)
    r = backtest.run(b, [Signal(idx[1], direction, stop, mid)], risk_cfg, slippage_points=0)
    assert r.trades.empty and r.rejections == {"gap_through_levels": 1}


def test_b_runs_through_backtester(bars, risk_cfg):
    from strategies.B_london_fade.strategy import LondonFade
    sigs = LondonFade().generate_signals(bars)
    ist = [s.time.tz_convert("Asia/Kolkata").time() for s in sigs]
    assert all(pd.Timestamp("13:30").time() < t <= pd.Timestamp("16:30").time() for t in ist)
    assert len({s.time.tz_convert("Asia/Kolkata").date() for s in sigs}) == len(sigs)   # one per day
    r = backtest.run(bars, sigs, risk_cfg)
    assert len(r.trades) > 0


# ---------------------------------------------------------------- C: SGE session long
def asian_cfg(risk_cfg):
    # TEST ONLY: the live profile's entry window (13:30–21:00 IST) blocks C's 06:30 IST entry (see Q-002).
    return {**risk_cfg, "entry_start_ist": "06:00", "entry_end_ist": "21:00"}


def test_c_signals_shape(bars):
    from strategies.C_sge_session_long.strategy import SgeSessionLong
    sigs = SgeSessionLong().generate_signals(bars)
    assert sigs
    for s in sigs:
        assert s.direction == 1 and s.target == float("inf") and s.stop < bars["close"].max() + 1e6
        assert s.time.hour == 1 and s.time.minute == 0 and s.time.dayofweek < 5
        assert s.exit_time - s.time == pd.Timedelta(hours=6, minutes=30)
        prev = bars.loc[:s.time - pd.Timedelta(minutes=15)]
        assert s.stop < prev["close"].iloc[-1]                   # stop below the signal close


def test_c_filter_uses_previous_western_session(bars):
    from strategies.C_sge_session_long.strategy import SgeSessionLong
    st = SgeSessionLong()
    loose = st.generate_signals(bars, {"west_drop_atr": 0.0})
    strict = st.generate_signals(bars, {"west_drop_atr": 1.0})
    nofilt = st.generate_signals(bars, {"benchmark": "no_filter"})
    assert len(strict) <= len(loose) <= len(nofilt)
    assert {s.time for s in strict} <= {s.time for s in loose} <= {s.time for s in nofilt}
    for s in strict:   # recompute W from data strictly before the entry
        d = s.time.normalize()
        prev = d - pd.Timedelta(days=3 if d.dayofweek == 0 else 1)
        w_end = bars.loc[:prev + pd.Timedelta(hours=20, minutes=45), "close"].iloc[-1]
        w_start = bars.loc[:prev + pd.Timedelta(hours=13, minutes=15), "close"].iloc[-1]
        assert w_end < w_start


def test_c_time_exit_and_benchmarks(bars, risk_cfg):
    from strategies.C_sge_session_long.strategy import SgeSessionLong
    st = SgeSessionLong()
    r = backtest.run(bars, st.generate_signals(bars), asian_cfg(risk_cfg))
    assert len(r.trades) > 0
    assert set(r.trades.reason) <= {"time_exit", "stop", "end_of_data"}
    te = r.trades[r.trades.reason == "time_exit"]
    assert not te.empty and (pd.to_datetime(te.exit_time).dt.strftime("%H:%M") == "07:30").all()
    r9 = backtest.run(bars, st.generate_signals(bars, {"exit_utc": "09:00"}), asian_cfg(risk_cfg))
    assert (pd.to_datetime(r9.trades[r9.trades.reason == "time_exit"].exit_time).dt.strftime("%H:%M") == "09:00").all()
    rnd = st.generate_signals(bars, {"benchmark": "random_hour", "benchmark_seed": 1})
    assert rnd == st.generate_signals(bars, {"benchmark": "random_hour", "benchmark_seed": 1})   # reproducible
    assert {s.time.normalize() for s in rnd} <= {s.time.normalize() for s in st.generate_signals(bars)}
    assert all(s.exit_time - s.time == pd.Timedelta(hours=6, minutes=30) for s in rnd)
    with pytest.raises(ValueError):
        st.generate_signals(bars, {"benchmark": "bogus"})


def test_c_blocked_by_current_live_profile(bars, risk_cfg):
    """Documents Q-002: with the unchanged 13:30–21:00 IST entry window every C entry is rejected."""
    from strategies.C_sge_session_long.strategy import SgeSessionLong
    r = backtest.run(bars, SgeSessionLong().generate_signals(bars), risk_cfg)
    assert r.trades.empty and r.rejections.get("outside_hours", 0) > 0


def test_time_exit_in_backtester(risk_cfg):
    idx = pd.date_range("2026-11-03 08:00", periods=12, freq="15min", tz="UTC")
    b = pd.DataFrame({"open": 2000.0, "high": 2000.5, "low": 1999.5, "close": 2000.0, "spread": 0}, index=idx)
    sig = Signal(idx[1], 1, 1990.0, float("inf"), exit_time=idx[6])
    t = backtest.run(b, [sig], risk_cfg, slippage_points=0).trades.iloc[0]
    assert t.reason == "time_exit" and t.exit_time == idx[6] and t.entry_time == idx[1]
