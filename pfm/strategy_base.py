"""Strategy interface. A strategy is a pure function of past bars → signals (no look-ahead)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Signal:
    time: pd.Timestamp      # close time of the bar that produced the signal (UTC); entry at next bar open
    direction: int          # +1 long, -1 short
    stop: float             # absolute stop price
    target: float           # absolute take-profit price
    tag: str = ""
    exit_time: pd.Timestamp | None = None   # optional time exit (UTC): close at the open of the first bar >= this


class Strategy:
    name = "base"
    default_params: dict = {}

    def generate_signals(self, bars: pd.DataFrame, params: dict | None = None) -> list[Signal]:
        raise NotImplementedError


def atr(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = bars["close"].shift()
    tr = pd.concat([bars["high"] - bars["low"], (bars["high"] - prev).abs(), (bars["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def h1_atr_on(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    """ATR(n) on H1, aligned to each lower-timeframe bar using only completed H1 bars."""
    h1 = bars.resample("1h", label="right", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    a = atr(h1, n)
    return a.reindex(bars.index, method="ffill")
