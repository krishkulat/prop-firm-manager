"""Frozen signal source for tests that guard the backtester and worker (R-022 item 5). Not a strategy.

The pinned trade counts and P&L in test_news.py and test_trailing.py were recorded with B v1.0 signals from the
pre-R-022 `breakout_events`, which reads the 23:45 IST bar (Q-010). R-022 fixed that, so B's own signals changed.
Those pins test the backtester and worker, not B, so they keep this frozen copy as input and do not move.
B's fixed behaviour is tested in test_strategies_bc.py and test_lookahead.py.
"""
from __future__ import annotations

import pandas as pd

from pfm.strategy_base import Signal, h1_atr_on
from strategies.A_asian_breakout.strategy import (ENTRY_END, ENTRY_START, IST, RANGE_END, RANGE_START,
                                                   BreakoutEvent)


def breakout_events_pre_r022(bars: pd.DataFrame, p: dict) -> list[BreakoutEvent]:
    """A's path as it was before R-022, with the Q-010 look-ahead. Do not fix, do not use for research."""
    a = h1_atr_on(bars)
    ist_open = bars.index.tz_convert(IST)
    bar_len = bars.index.to_series().diff().median()
    ist_close = ist_open + bar_len                       # bar close time in IST
    df = bars.assign(atr=a.values, d=ist_open.date, t_open=ist_open.time, t_close=ist_close.time)

    events: list[BreakoutEvent] = []
    for day, g in df.groupby("d", sort=True):
        rng = g[(g.t_open >= RANGE_START) & (g.t_close <= RANGE_END)]
        if len(rng) < 8:
            continue
        hi, lo = rng["high"].max(), rng["low"].min()
        win = g[(g.t_close > ENTRY_START) & (g.t_close <= ENTRY_END)]
        if win.empty:
            continue
        atr_now = win["atr"].iloc[0]
        if pd.isna(atr_now) or atr_now <= 0:
            continue
        width = hi - lo
        if not (p["min_range_atr"] * atr_now <= width <= p["max_range_atr"] * atr_now):
            continue
        mid = (hi + lo) / 2
        for ts, row in win.iterrows():
            c = row["close"]
            if c > hi:
                d = 1
            elif c < lo:
                d = -1
            else:
                continue
            atr_stop = c - d * p["stop_atr"] * atr_now
            stop = max(mid, atr_stop) if d == 1 else min(mid, atr_stop)   # tighter of the two
            risk = abs(c - stop)
            if risk <= 0:
                break
            events.append(BreakoutEvent(ts + bar_len, d, c, risk))
            break   # one trade per day
    return events


class LondonFadePreR022:
    """B v1.0 on the frozen path. `name` is "B" so the worker can run it in place of the registry's B."""
    name = "B"
    default_params = {"rr": 2.0, "stop_atr": 1.2, "min_range_atr": 1.5, "max_range_atr": 4.0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        return [Signal(e.signal_time, -e.direction, e.close + e.direction * e.risk,
                       e.close - e.direction * p["rr"] * e.risk, "B")
                for e in breakout_events_pre_r022(bars, p)]
