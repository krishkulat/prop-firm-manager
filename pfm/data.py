"""Market data: load CSV bars, enforce the sealed holdout, export from MT5, make synthetic data for tests."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import ROOT
from .config import business

IST = "Asia/Kolkata"


def _path(symbol: str, timeframe: str) -> Path:
    return ROOT / "data" / f"{symbol}_{timeframe}.csv"


def holdout_start(df: pd.DataFrame, months: int | None = None) -> pd.Timestamp:
    months = months if months is not None else business()["research"]["holdout_months"]
    return df.index.max() - pd.DateOffset(months=months)


def load(symbol: str = "XAUUSD", timeframe: str = "M15", split: str = "research",
         path: str | Path | None = None, holdout_months: int | None = None) -> pd.DataFrame:
    """Bars indexed by UTC time. split: research (holdout removed) | holdout (only holdout) | all.

    'holdout' and 'all' are for the Validation agent only (AGENTS.md rule 5).
    """
    p = Path(path) if path else _path(symbol, timeframe)
    df = pd.read_csv(p, parse_dates=["time"]).set_index("time").sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    if "spread" not in df:
        df["spread"] = business()["research"]["costs"]["spread_points_default"]
    cut = holdout_start(df, holdout_months)
    if split == "research":
        return df[df.index < cut]
    if split == "holdout":
        return df[df.index >= cut]
    if split == "all":
        return df
    raise ValueError(f"unknown split {split}")


def synthetic(days: int = 400, seed: int = 7, start: str = "2023-01-02") -> pd.DataFrame:
    """Random-walk XAUUSD-like M15 bars with an Asian lull and London volatility. For tests only."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=days * 96, freq="15min", tz="UTC")
    idx = idx[idx.dayofweek < 5]
    hour = idx.hour
    vol = np.where((hour >= 7) & (hour < 16), 1.6, np.where(hour < 7, 0.6, 1.0))
    rets = rng.normal(0, 0.9, len(idx)) * vol
    close = 2000 + np.cumsum(rets)
    open_ = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.normal(0, 0.6, len(idx))) * vol
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "spread": 25}, index=idx).rename_axis("time")


def export_mt5(symbol: str, timeframe: str, start: str) -> Path:  # pragma: no cover - needs Windows + MT5
    import MetaTrader5 as mt5  # type: ignore
    tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    rates = mt5.copy_rates_range(symbol, tf, pd.Timestamp(start).to_pydatetime(), pd.Timestamp.utcnow().to_pydatetime())
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit("no data returned; open the symbol chart and scroll back to load history")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")  # MT5 server time; convert if your broker is not UTC
    out = _path(symbol, timeframe)
    df[["time", "open", "high", "low", "close", "spread"]].to_csv(out, index=False)
    return out


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--symbol", default="XAUUSD")
    e.add_argument("--timeframe", default="M15")
    e.add_argument("--start", default="2019-01-01")
    a = ap.parse_args()
    print(export_mt5(a.symbol, a.timeframe, a.start))
