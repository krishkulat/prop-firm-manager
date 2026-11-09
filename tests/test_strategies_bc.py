"""Strategies B (H-002) and C (H-003) on the synthetic fixture."""
import hashlib
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


def test_range_does_not_read_bars_after_the_entry_window(bars):
    """Q-010, from dev/R-019 without its xfail mark: the 23:45 IST bar closes at 00:00 and must not join the range.
    Changed from the branch: one day's 23:45 bar at a time, and only events up to that day compared. Moving every
    23:45 bar by 50 also moves the H1 ATR of the following mornings, which those days may read."""
    from strategies.A_asian_breakout.strategy import breakout_events
    from strategies.B_london_fade.strategy import LondonFade
    p = LondonFade.default_params
    k = lambda ev, end: [(e.signal_time, e.direction, e.close, e.risk) for e in ev if e.signal_time < end]
    base = breakout_events(bars, p)
    ist = bars.index.tz_convert("Asia/Kolkata")
    days = [pd.Timestamp("2023-03-06").date()] + [e.signal_time.tz_convert("Asia/Kolkata").date() for e in base[::12]]
    for day in days:                                         # 2023-03-06 is the day Q-010 used as proof
        late = bars.copy()
        last = (ist.date == day) & (ist.strftime("%H:%M") == "23:45")            # 7 h after the entry window ends
        assert last.sum() == 1
        late.loc[last, "high"] += 50
        late.loc[last, "low"] -= 50
        end = late.index[last][0]
        assert k(base, end) and k(breakout_events(late, p), end) == k(base, end)
    assert any(e.signal_time.tz_convert("Asia/Kolkata").date() == days[0] for e in base)


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


def test_frozen_pre_r022_source_is_the_old_path_and_b_is_not():
    """tests/legacy_pre_r022.py must equal breakout_events as it was before R-022. The hashes were recorded from main
    at 7c2b194 (dev/R-019 EVENT_PINS). B's fixed path must give different events on the same bars."""
    from strategies.A_asian_breakout.strategy import breakout_events
    from strategies.B_london_fade.strategy import LondonFade
    from tests.legacy_pre_r022 import breakout_events_pre_r022
    pins = [(200, 66, "e1e09f31f70b57ce531f0ef12392260e9d559b6177b7e43d46bbe59f2e1e67ed"),
            (900, 275, "9f405ed23a8fc5138ff5a43fece6591d6f36565d8ab0d71c46c3b299f0d0675b")]
    fmt = lambda ev: "\n".join(f"{e.signal_time.isoformat()},{e.direction},{e.close:.6f},{e.risk:.6f}" for e in ev)
    for days, count, digest in pins:
        b = data.synthetic(days=days)
        old = breakout_events_pre_r022(b, LondonFade.default_params)
        assert len(old) == count and hashlib.sha256(fmt(old).encode()).hexdigest() == digest
        assert fmt(breakout_events(b, LondonFade.default_params)) != fmt(old)
