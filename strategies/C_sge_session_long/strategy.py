"""Strategy C — long gold in the SGE day session after a Western-hours drop (H-003).
Mirrors mql5/Experts/SgeLong_C.mq5.

Rules (all times UTC; China has no DST):
- W = close at 21:00 minus close at 13:30 of the previous trading day, in units of H1 ATR(14) at 21:00.
  "Close at T" = close of the last M15 bar whose close time is <= T and > T − 30 min (else the day is skipped).
- If W <= −west_drop_atr: long at the open of the 01:00 bar (signal = close of the 00:45 bar).
- Stop = signal close − stop_atr × H1 ATR(14) (completed H1 bars only). No target. Time exit at exit_utc.
- Long only, one trade per day, Mon–Fri.

Benchmarks for the H-003 kill criteria (not tunable parameters):
- benchmark: none        the strategy
- benchmark: no_filter   long every weekday at 01:00, same stop and exit (W condition dropped)
- benchmark: random_hour same days as the strategy, entry at a random whole UTC hour with the same hold length
                         and stop rule (seeded by benchmark_seed, so a run is reproducible)
"""
from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

from pfm.strategy_base import Signal, Strategy, h1_atr_on

ENTRY_UTC = time(1, 0)
WEST_START_UTC, WEST_END_UTC = time(13, 30), time(21, 0)
BENCHMARKS = ("none", "no_filter", "random_hour")


def _hm(x) -> time:
    if isinstance(x, time):
        return x
    h, m = str(x).split(":")
    return time(int(h), int(m))


class SgeSessionLong(Strategy):
    name = "C"
    default_params = {"west_drop_atr": 0.5, "stop_atr": 2.0, "exit_utc": "07:30",
                      "benchmark": "none", "benchmark_seed": 0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        p = {**self.default_params, **(params or {})}
        bench = p["benchmark"]
        if bench not in BENCHMARKS:
            raise ValueError(f"benchmark must be one of {BENCHMARKS}, got {bench!r}")
        exit_t = _hm(p["exit_utc"])
        hold = pd.Timedelta(hours=exit_t.hour - ENTRY_UTC.hour, minutes=exit_t.minute - ENTRY_UTC.minute)
        if hold <= pd.Timedelta(0):
            raise ValueError("exit_utc must be after 01:00 UTC")

        bar_len = bars.index.to_series().diff().median()
        atr = pd.Series(h1_atr_on(bars).values, index=bars.index)
        close_t = bars.index + bar_len                                   # bar close times (UTC)
        closes = pd.Series(bars["close"].values, index=close_t)          # indexed by close time
        atr_c = pd.Series(atr.values, index=close_t)                     # ATR known at each bar's close
        days = sorted(set(bars.index.normalize()))
        tol = pd.Timedelta(minutes=30)

        def close_at(t: pd.Timestamp):
            s = closes.loc[t - tol + pd.Timedelta(seconds=1):t]
            return (s.iloc[-1], s.index[-1]) if len(s) else (None, None)

        # Western-hours return per UTC date, in ATR units
        west: dict = {}
        for d in days:
            c_end, t_end = close_at(d + pd.Timedelta(hours=WEST_END_UTC.hour, minutes=WEST_END_UTC.minute))
            c_start, _ = close_at(d + pd.Timedelta(hours=WEST_START_UTC.hour, minutes=WEST_START_UTC.minute))
            if c_end is None or c_start is None:
                continue
            a = atr_c.loc[t_end]
            if pd.isna(a) or a <= 0:
                continue
            west[d] = (c_end - c_start) / a

        rng = np.random.default_rng(int(p["benchmark_seed"]))
        last_entry_hour = 23 - int(np.ceil(hold / pd.Timedelta(hours=1)))
        out: list[Signal] = []
        prev_trading_day = None
        for d in days:
            w = west.get(prev_trading_day) if prev_trading_day is not None else None
            if d in west:
                prev_trading_day = d
            if d.dayofweek >= 5:
                continue
            if bench != "no_filter" and (w is None or w > -p["west_drop_atr"]):
                continue
            entry_ts = d + pd.Timedelta(hours=ENTRY_UTC.hour, minutes=ENTRY_UTC.minute)
            if bench == "random_hour":
                entry_ts = d + pd.Timedelta(hours=int(rng.integers(0, last_entry_hour + 1)))
            sig_ts = entry_ts                                  # = close time of the bar before the entry bar
            if entry_ts not in bars.index:
                continue
            c_sig, t_sig = close_at(sig_ts)
            if c_sig is None or t_sig != sig_ts:
                continue
            a = atr_c.loc[t_sig]
            if pd.isna(a) or a <= 0:
                continue
            out.append(Signal(sig_ts, 1, c_sig - p["stop_atr"] * a, float("inf"),
                              "C" if bench == "none" else f"C-{bench}", exit_time=entry_ts + hold))
        return out
