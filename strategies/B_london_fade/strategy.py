"""Strategy B — Asian-range false-breakout fade at the London open (H-002), v1.1.

Per R-004 this reuses strategy A's audited range/session/stop code path (`breakout_events`) exactly; only the
entry side flips. Same signal times and stop distance as v1.0. v1.1 (R-019) replaces the rr target with the Asian
range midpoint, for both sides:
  close above range high → SELL, stop = close + risk, target = range midpoint
  close below range low  → BUY,  stop = close − risk, target = range midpoint
An entry bar that opens at or past the midpoint fails the backtester's geometry check (`gap_through_levels`), so
there is no trade that day.

mql5/Experts/LondonFade_B.mq5 is still v1.0 (InpRR target). R-019: the EA changes only if v1.1 passes the gate.
"""
from __future__ import annotations

import pandas as pd

from pfm.strategy_base import Signal, Strategy
from strategies.A_asian_breakout.strategy import breakout_events


class LondonFade(Strategy):
    name = "B"
    default_params = {"stop_atr": 1.2, "min_range_atr": 1.5, "max_range_atr": 4.0}   # A v1.1 values, without rr

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        out: list[Signal] = []
        for e in breakout_events(bars, p):
            d = -e.direction                                  # fade the break
            out.append(Signal(e.signal_time, d, e.close - d * e.risk, e.mid, "B"))
        return out
