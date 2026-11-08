"""No look-ahead in any Python strategy on `main` (R-022 item 3).

A signal stamped at T (entry at the open of the bar starting at T) may use bars that opened before T and the open of
the bar at T, nothing else. So for every cut time T: the signals at or before T on the full bars must equal the
signals on bars cut at T, where the bar at T keeps its open and has its high, low and close set to that open.
Cut times are fixed clock times on sampled days, including 18:00 UTC (just before the 23:45 IST bar, Q-010), plus
every signal time the full run gives on those days.
"""
import importlib

import pandas as pd
import pytest

from pfm import data

STRATEGIES = [   # (module, class, benchmarks other than "none")
    ("A_asian_breakout", "AsianBreakout", ()),
    ("B_london_fade", "LondonFade", ()),
    ("C_sge_session_long", "SgeSessionLong", ("no_filter", "random_hour")),
    ("E_us_open_impulse", "UsOpenImpulse", ("random_side", "opposite_side", "no_filter")),
    ("F_asian_rise_short", "AsianRiseShort", ("random_side", "opposite_side", "no_filter")),
    ("G_prior_day_failed_break", "PriorDayFailedBreak", ("random_side", "opposite_side", "no_reclaim", "shifted_level")),
]
CASES = [(m, c, b) for m, c, benches in STRATEGIES for b in ("none", *benches)]
CLOCK_UTC = ["00:00", "01:00", "06:45", "08:00", "08:30", "10:15", "11:00", "13:30", "14:30", "15:15", "16:30",
             "18:00", "18:15", "21:45"]
N_DAYS = 8


@pytest.fixture(scope="module")
def bars():
    return data.synthetic(days=170, start="2023-01-02")       # spans the March DST change in New York and London


def key(s):
    return (s.time, s.direction, round(s.stop, 9), round(s.target, 9) if s.target != float("inf") else s.target,
            s.exit_time)


def cut_at(bars, t):
    c = bars.loc[:t].copy()
    if len(c) and c.index[-1] == t:                            # only the open of the bar at T is known at T
        o = c.iloc[-1]["open"]
        c.iloc[-1, c.columns.get_indexer(["high", "low", "close"])] = o
    return c


def cut_times(bars, full_sigs):
    days = sorted(set(bars.index.normalize()))
    days = [d for d in days[25::(len(days) - 25) // N_DAYS] if d.dayofweek < 5][:N_DAYS]
    ts = {d + pd.Timedelta(hc) for d in days for hc in (f"{h}:00" for h in CLOCK_UTC)}
    ts |= {s.time for s in full_sigs if s.time.normalize() in days}
    return sorted(t for t in ts if t in bars.index)


@pytest.mark.parametrize("module, cls, bench", CASES, ids=[f"{m[0]}-{b}" for m, _, b in CASES])
def test_signals_up_to_t_do_not_depend_on_later_bars(bars, module, cls, bench):
    strat = getattr(importlib.import_module(f"strategies.{module}.strategy"), cls)()
    params = {} if bench == "none" else {"benchmark": bench}
    full = strat.generate_signals(bars, params)
    times = cut_times(bars, full)
    assert len(times) >= N_DAYS * 10
    checked = 0
    for t in times:
        want = [key(s) for s in full if s.time <= t]
        got = [key(s) for s in strat.generate_signals(cut_at(bars, t), params) if s.time <= t]
        assert got == want, f"{module} {bench}: signals up to {t} change when later bars are removed"
        checked += sum(1 for s in full if s.time == t)
    assert checked >= 1 or not full                            # at least one cut lands exactly on a signal
