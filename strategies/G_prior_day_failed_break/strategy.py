"""Strategy G — failed break of the prior day's high or low, faded inside 13:30-21:00 IST (H-007).
Python only until G passes `backtested` (R-021). There is no EA.

Rules (the day is New York, everything else is fixed UTC):
- Day = 17:00 to 17:00 New York, by bar open time, on America/New_York. Bars of a Saturday or Sunday day (after the
  Friday close) belong to no day, but still count for liveness.
- PDH, PDL = high and low of the last completed Monday-Friday day.
- A level has one chance. The first bar to trade beyond it decides, from the end of the prior day, Asia included:
  it is a break only if it opens 08:00-15:00 UTC (both ends in), goes beyond by >= 0.10 x ATR, and does not open
  within 60 minutes after an NFP or CPI release. Anything else leaves the level dead for the day, a smaller poke too.
- Reclaim: within reclaim_bars M15 bars, counting the break bar, a bar closes back inside the level.
- Entry: open of the next M15 bar, against the break. Last entry bar opens 15:15 UTC.
- Stop = entry bar open +/- stop_atr x ATR, placed with the order. Target = target_r x that distance. ATR(14, H1) comes
  from the last H1 bar closed at or before the signal. The entry bar open is the only value read from the entry bar.
- If the break's extreme (break bar through reclaim bar) is at or beyond the stop, skip it: the other level may still
  give the day's trade. One trade a day, first valid signal. Both levels on one entry bar: order unknown, no trade.
- Time exit 16:30 UTC (22:00 IST).

Benchmarks for the H-007 kill criteria (not tunable parameters):
- benchmark: none           the strategy
- benchmark: random_side    same entries, stop and target distances, random side (seeded by benchmark_seed)
- benchmark: opposite_side  same, with the break instead of against it
- benchmark: no_reclaim     fade the first break at the next bar open, same stop and target
- benchmark: shifted_level  levels moved outward by 0.25 x prior-day range; liveness and break judged on the moved level
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from functools import lru_cache

import numpy as np
import pandas as pd

from pfm import ROOT
from pfm.strategy_base import Signal, Strategy, h1_atr_on

NY = "America/New_York"
BREAK_START, BREAK_END = time(8, 0), time(15, 0)       # bar open, UTC, both ends in
LAST_ENTRY, EXIT_UTC = time(15, 15), time(16, 30)
BREAK_MARGIN_ATR = 0.10
NEWS_EXCLUSION = pd.Timedelta(minutes=60)
SHIFT_RANGE = 0.25
CALENDAR = ROOT / "research/news/usd_high_impact.csv"
BENCHMARKS = ("none", "random_side", "opposite_side", "no_reclaim", "shifted_level")


@lru_cache(maxsize=1)
def release_times() -> pd.DatetimeIndex:
    """NFP and CPI releases from the reviewed calendar. A missing file raises: no silent run without the exclusion."""
    cal = pd.read_csv(CALENDAR)
    return pd.DatetimeIndex(pd.to_datetime(cal.loc[cal["event"].isin(["NFP", "CPI"]), "time"], utc=True)).sort_values()


def just_after_release(ts: pd.Timestamp) -> bool:
    times = release_times()
    i = times.searchsorted(ts, side="right") - 1
    return i >= 0 and ts - times[i] <= NEWS_EXCLUSION


def trading_day(index: pd.DatetimeIndex) -> np.ndarray:
    """New York day of each bar open: 17:00 New York starts the next date. Follows DST through the tz database."""
    return (index.tz_convert(NY).tz_localize(None) + pd.Timedelta(hours=7)).normalize().to_numpy()


@dataclass
class Candidate:
    side: int        # +1 the high was broken, -1 the low
    entry: int       # position of the entry bar
    extreme: float   # furthest price from the break bar through the reclaim bar


def _break_bar(side, level, first, last, high, low, times, atr):
    """Position of the level's break, or None. The first bar beyond the level decides."""
    extreme = high if side == 1 else low
    beyond = side * (extreme[first:last + 1] - level)
    hits = np.flatnonzero(beyond > 0)
    if hits.size == 0:
        return None
    i, by = first + int(hits[0]), beyond[hits[0]]
    if not BREAK_START <= times[i].time() <= BREAK_END or not by >= BREAK_MARGIN_ATR * atr[i]:   # a NaN ATR fails too
        return None
    return None if just_after_release(times[i]) else i


def _candidate(side, level, first, last, reclaim_bars, no_reclaim, high, low, close, times, atr):
    i = _break_bar(side, level, first, last, high, low, times, atr)
    if i is None:
        return None
    end = min(i + reclaim_bars - 1, last)
    closed_in = np.flatnonzero(side * (close[i:end + 1] - level) < 0)
    if no_reclaim:
        j = i
    elif closed_in.size:
        j = i + int(closed_in[0])
    else:
        return None
    if j + 1 >= len(times) or times[j + 1].date() != times[i].date() or times[j + 1].time() > LAST_ENTRY:
        return None
    extreme = high[i:j + 1].max() if side == 1 else low[i:j + 1].min()
    return Candidate(side, j + 1, extreme)


def scan(bars: pd.DataFrame, params: dict | None = None) -> tuple[list[Signal], dict]:
    """The day-by-day scan. Returns the signals and how many candidates each skip rule dropped."""
    p = {**PriorDayFailedBreak.default_params, **(params or {})}
    bench, reclaim_bars = p["benchmark"], int(p["reclaim_bars"])
    if bench not in BENCHMARKS:
        raise ValueError(f"benchmark must be one of {BENCHMARKS}, got {bench!r}")
    if reclaim_bars < 1:
        raise ValueError("reclaim_bars must be at least 1")

    times, days = bars.index, trading_day(bars.index)
    high, low = bars["high"].to_numpy(), bars["low"].to_numpy()
    close, open_ = bars["close"].to_numpy(), bars["open"].to_numpy()
    atr = np.asarray(h1_atr_on(bars), dtype=float)                       # completed H1 bars only
    rng = np.random.default_rng(int(p["benchmark_seed"]))

    bounds = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])          # first bar of each run of one day
    spans = [(int(a), int(b) - 1) for a, b in zip(bounds, np.r_[bounds[1:], len(days)])]
    spans = [s for s in spans if pd.Timestamp(days[s[0]]).dayofweek < 5]

    out: list[Signal] = []
    skips = {"extreme_beyond_stop": 0, "both_levels_same_entry": 0}
    for (p_first, p_last), (first, last) in zip(spans, spans[1:]):
        pdh, pdl = high[p_first:p_last + 1].max(), low[p_first:p_last + 1].min()
        if bench == "shifted_level":
            shift = SHIFT_RANGE * (pdh - pdl)
            pdh, pdl = pdh + shift, pdl - shift
        found = [c for c in (_candidate(s, lvl, p_last + 1, last, reclaim_bars, bench == "no_reclaim",
                                        high, low, close, times, atr)
                             for s, lvl in ((1, pdh), (-1, pdl))) if c is not None]
        found.sort(key=lambda c: c.entry)
        if len(found) == 2 and found[0].entry == found[1].entry:
            skips["both_levels_same_entry"] += 1
            continue
        for c in found:
            a, o = atr[c.entry], open_[c.entry]                          # the only value read from the entry bar
            if np.isnan(a) or a <= 0:
                continue
            dist = p["stop_atr"] * a
            if c.side * (c.extreme - (o + c.side * dist)) >= 0:          # judged on the fade's stop, for every benchmark
                skips["extreme_beyond_stop"] += 1
                continue
            d = -c.side
            if bench == "opposite_side":
                d = c.side
            elif bench == "random_side":
                d = 1 if rng.integers(0, 2) else -1
            t = times[c.entry]
            out.append(Signal(t, d, o - d * dist, o + d * p["target_r"] * dist, "G" if bench == "none" else f"G-{bench}",
                              exit_time=t.normalize() + pd.Timedelta(hours=EXIT_UTC.hour, minutes=EXIT_UTC.minute)))
            break
    return out, skips


class PriorDayFailedBreak(Strategy):
    name = "G"
    default_params = {"reclaim_bars": 2, "stop_atr": 1.25, "target_r": 2.0, "benchmark": "none", "benchmark_seed": 0}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        return scan(bars, params)[0]
