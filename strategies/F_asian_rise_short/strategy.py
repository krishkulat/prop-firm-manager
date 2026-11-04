"""Strategy F — short after an Asian-session rise (H-006). Mirrors mql5/Experts/AsianRiseShort_F.mq5.

Rules (R and the entry are fixed UTC, the exit is New York):
- R = (open of the 08:00 UTC M15 bar − open of the 01:00 UTC M15 bar) / H1 ATR(14).
  ATR comes from the last H1 bar closed at or before 08:00 UTC.
- If R >= asia_rise_atr: short at the open of the 08:00 UTC bar (13:30 IST, the first bar the window allows).
- Stop = open of the 08:00 bar + stop_atr × ATR, placed with the order. No target. Time exit at exit_et (ET).
  That open is known at entry, so unlike C and E the stop does not use the previous bar's close.
- One trade a day, Mon–Fri. A day missing the 01:00 or 08:00 bar, or a usable ATR, is skipped.

Benchmarks for the H-006 kill criteria (not tunable parameters):
- benchmark: none          the strategy
- benchmark: random_side   same days, times and stop distance, random side (seeded by benchmark_seed)
- benchmark: opposite_side same days, times and stop distance, long
- benchmark: no_filter     short every day, including days Asia fell. Not asia_rise_atr = 0, which would drop those.
"""
from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

from pfm.strategy_base import Signal, Strategy, h1_atr_on

NY = "America/New_York"
RISE_START_UTC, ENTRY_UTC = time(1, 0), time(8, 0)
LATEST_ENTRY_ET = time(4, 0)          # 08:00 UTC in US summer time; 03:00 ET in winter
BENCHMARKS = ("none", "random_side", "opposite_side", "no_filter")


def _hm(x) -> time:
    if isinstance(x, time):
        return x
    h, m = str(x).split(":")
    return time(int(h), int(m))


def _utc(day, t: time) -> pd.Timestamp:
    return pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=t.hour, minute=t.minute, tz="UTC")


def _ny(day, t: time) -> pd.Timestamp:
    """UTC instant of New York wall-clock time t on date day."""
    return pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=t.hour, minute=t.minute,
                        tz=NY).tz_convert("UTC")


class AsianRiseShort(Strategy):
    name = "F"
    default_params = {"asia_rise_atr": 0.5, "stop_atr": 2.0, "exit_et": "11:00",
                      "benchmark": "none", "benchmark_seed": 0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        bench = p["benchmark"]
        if bench not in BENCHMARKS:
            raise ValueError(f"benchmark must be one of {BENCHMARKS}, got {bench!r}")
        exit_t = _hm(p["exit_et"])
        if exit_t <= LATEST_ENTRY_ET:
            raise ValueError("exit_et must be after 04:00 ET")

        atr = pd.Series(h1_atr_on(bars).values, index=bars.index)        # completed H1 bars only
        rng = np.random.default_rng(int(p["benchmark_seed"]))
        out: list[Signal] = []
        for day in sorted(set(bars.index.date)):
            if day.weekday() >= 5:
                continue
            start, entry = _utc(day, RISE_START_UTC), _utc(day, ENTRY_UTC)
            if start not in bars.index or entry not in bars.index:
                continue
            a = atr.loc[entry]
            if pd.isna(a) or a <= 0:
                continue
            o = bars.at[entry, "open"]                                   # the only value read from the entry bar
            if bench != "no_filter" and (o - bars.at[start, "open"]) / a < p["asia_rise_atr"]:
                continue
            side = -1
            if bench == "opposite_side":
                side = 1
            elif bench == "random_side":
                side = 1 if rng.integers(0, 2) else -1
            out.append(Signal(entry, side, o - side * p["stop_atr"] * a, side * float("inf"),
                              "F" if bench == "none" else f"F-{bench}", exit_time=_ny(day, exit_t)))
        return out
