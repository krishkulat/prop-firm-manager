"""Strategy B — Asian-range false-breakout fade at the London open (H-002).
Mirrors mql5/Experts/LondonFade_B.mq5.

Per R-004 this reuses strategy A's audited range/session/stop code path (`breakout_events`) exactly; only the
entry side flips. Same signal times, same stop distance, target = rr × that distance, as in audit-R002-2.
  close above range high → SELL, stop = close + risk, target = close − rr × risk
  close below range low  → BUY,  stop = close − risk, target = close + rr × risk
"""
from __future__ import annotations

import pandas as pd

from pfm.strategy_base import Signal, Strategy
from strategies.A_asian_breakout.strategy import breakout_events


class LondonFade(Strategy):
    name = "B"
    default_params = {"rr": 2.0, "stop_atr": 1.2, "min_range_atr": 1.5, "max_range_atr": 4.0}   # = A v1.1

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        out: list[Signal] = []
        for e in breakout_events(bars, p):
            d = -e.direction                                  # fade the break
            out.append(Signal(e.signal_time, d, e.close - d * e.risk, e.close + d * p["rr"] * e.risk, "B"))
        return out
