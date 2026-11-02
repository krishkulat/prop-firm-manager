"""Strategies B (H-002) and C (H-003) on the synthetic fixture."""
import math

import pandas as pd
import pytest

from pfm import backtest, data
from pfm.strategy_base import Signal


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
        risk_a = abs(ca - sa.stop)
        assert math.isclose(abs(sb.stop - ca), risk_a, rel_tol=1e-9)        # same stop distance
        assert math.isclose(abs(sb.target - ca), 2.0 * risk_a, rel_tol=1e-9)
        assert (sb.direction == 1 and sb.stop < ca < sb.target) or (sb.direction == -1 and sb.target < ca < sb.stop)


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
