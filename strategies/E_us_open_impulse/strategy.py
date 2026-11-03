"""Strategy E — US-open impulse continuation (H-004). Mirrors mql5/Experts/UsOpenImpulse_E.mq5.

Rules (all clock times New York, so DST follows the US data clock):
- I = (close of the 09:15 ET M15 bar − open of the 08:30 ET M15 bar) / H1 ATR(14).
  ATR comes from the last H1 bar closed at or before 09:30 ET.
- If |I| >= impulse_atr: trade in the direction of I at the open of the 09:30 ET bar (19:00 or 20:00 IST).
- Stop = signal close ∓ stop_atr × ATR, placed with the order. No target. Time exit at exit_et.
- One trade a day, Mon–Fri. A day missing any of the three bars is skipped.

Benchmarks for the H-004 kill criteria (not tunable parameters):
- benchmark: none          the strategy
- benchmark: random_side   same days, times and stop distance, random side (seeded by benchmark_seed)
- benchmark: opposite_side same days, times and stop distance, opposite side
- benchmark: no_filter     impulse_atr = 0: every day with a non-zero impulse, in its direction
"""
from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

from pfm.strategy_base import Signal, Strategy, h1_atr_on

NY = "America/New_York"
IMPULSE_OPEN_ET, LAST_IMPULSE_BAR_ET, ENTRY_ET = time(8, 30), time(9, 15), time(9, 30)
BENCHMARKS = ("none", "random_side", "opposite_side", "no_filter")


def _hm(x) -> time:
    if isinstance(x, time):
        return x
    h, m = str(x).split(":")
    return time(int(h), int(m))


def _at(day, t: time) -> pd.Timestamp:
    """UTC instant of New York wall-clock time t on New York date day."""
    return pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=t.hour, minute=t.minute,
                        tz=NY).tz_convert("UTC")


class UsOpenImpulse(Strategy):
    name = "E"
    default_params = {"impulse_atr": 1.0, "stop_atr": 1.5, "exit_et": "11:30",
                      "benchmark": "none", "benchmark_seed": 0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        bench = p["benchmark"]
        if bench not in BENCHMARKS:
            raise ValueError(f"benchmark must be one of {BENCHMARKS}, got {bench!r}")
        exit_t = _hm(p["exit_et"])
        if exit_t <= ENTRY_ET:
            raise ValueError("exit_et must be after 09:30 ET")
        threshold = 0.0 if bench == "no_filter" else p["impulse_atr"]

        atr = pd.Series(h1_atr_on(bars).values, index=bars.index)        # completed H1 bars only
        rng = np.random.default_rng(int(p["benchmark_seed"]))
        out: list[Signal] = []
        for day in sorted(set(bars.index.tz_convert(NY).date)):
            if day.weekday() >= 5:
                continue
            first, last, entry = (_at(day, t) for t in (IMPULSE_OPEN_ET, LAST_IMPULSE_BAR_ET, ENTRY_ET))
            if first not in bars.index or last not in bars.index or entry not in bars.index:
                continue
            a = atr.loc[entry]
            if pd.isna(a) or a <= 0:
                continue
            c = bars.at[last, "close"]
            impulse = (c - bars.at[first, "open"]) / a
            if impulse == 0 or abs(impulse) < threshold:
                continue
            side = 1 if impulse > 0 else -1
            if bench == "opposite_side":
                side = -side
            elif bench == "random_side":
                side = 1 if rng.integers(0, 2) else -1
            out.append(Signal(entry, side, c - side * p["stop_atr"] * a, side * float("inf"),
                              "E" if bench == "none" else f"E-{bench}", exit_time=_at(day, exit_t)))
        return out
