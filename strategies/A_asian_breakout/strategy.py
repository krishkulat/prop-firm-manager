"""Strategy A — Asian-range breakout at the London open (H-001). Mirrors mql5/Experts/GoldBreakout_A.mq5.

The range / session / stop code path lives in `breakout_events()` so that strategy B (H-002, the fade) reuses the
audited path exactly and only flips the entry side (R-004).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

from pfm.strategy_base import Signal, Strategy, h1_atr_on

IST = "Asia/Kolkata"
RANGE_START, RANGE_END = time(5, 30), time(12, 30)
ENTRY_START, ENTRY_END = time(13, 30), time(16, 30)


@dataclass
class BreakoutEvent:
    signal_time: pd.Timestamp   # close time of the breakout bar (UTC); entry at the next bar's open
    direction: int              # +1 close above range high, -1 close below range low
    close: float                # close of the breakout bar
    risk: float                 # stop distance: tighter of range midpoint and stop_atr × H1 ATR


def breakout_events(bars: pd.DataFrame, p: dict) -> list[BreakoutEvent]:
    """First M15 close beyond the 05:30–12:30 IST range inside 13:30–16:30 IST, at most one per IST day."""
    a = h1_atr_on(bars)
    ist_open = bars.index.tz_convert(IST)
    bar_len = bars.index.to_series().diff().median()
    ist_close = ist_open + bar_len                       # bar close time in IST
    df = bars.assign(atr=a.values, d=ist_open.date, t_open=ist_open.time, t_close=ist_close.time)

    events: list[BreakoutEvent] = []
    for day, g in df.groupby("d", sort=True):
        rng = g[(g.t_open >= RANGE_START) & (g.t_open < RANGE_END)]
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


class AsianBreakout(Strategy):
    name = "A"
    default_params = {"rr": 2.0, "stop_atr": 1.2, "min_range_atr": 1.5, "max_range_atr": 4.0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        return [Signal(e.signal_time, e.direction, e.close - e.direction * e.risk,
                       e.close + e.direction * p["rr"] * e.risk, "A")
                for e in breakout_events(bars, p)]
