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


def server_to_utc(server_times: pd.Series, server_tz: str) -> pd.Series:
    """Convert MT5 bar times (broker server time, naive) to UTC.

    server_tz: 'nyclose' = UTC+2 in winter / UTC+3 in summer, switching with US daylight saving (the most
    common MT5 broker clock: 17:00 New York = 00:00 server); or a fixed offset in hours such as '2' or '0'.
    """
    s = pd.to_datetime(server_times)
    if server_tz == "nyclose":
        ny = (s - pd.Timedelta(hours=7)).dt.tz_localize("America/New_York", ambiguous=False,
                                                         nonexistent="shift_forward")
        return ny.dt.tz_convert("UTC").dt.tz_localize(None)
    return s - pd.Timedelta(hours=float(server_tz))


def _resolve_symbol(mt5, wanted: str) -> str:  # pragma: no cover - needs MT5
    candidates = [wanted, wanted + ".r", wanted + "m", wanted + ".", "GOLD", "XAUUSD.raw", "XAUUSD+", "XAUUSD.pro"]
    for name in candidates:
        if mt5.symbol_info(name) is not None and mt5.symbol_select(name, True):
            return name
    gold = [s.name for s in (mt5.symbols_get() or []) if "XAU" in s.name.upper() or "GOLD" in s.name.upper()]
    raise SystemExit(f"Symbol '{wanted}' not found at this broker. Gold symbols available: {gold or 'none'}. "
                     f"Re-run with --symbol <one of these>.")


def export_mt5(symbol: str, timeframe: str, start: str, server_tz: str = "nyclose",
               out_symbol: str = "XAUUSD") -> Path:  # pragma: no cover - needs Windows + MT5
    import MetaTrader5 as mt5  # type: ignore
    tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}. Is MT5 open and logged in?")
    try:
        name = _resolve_symbol(mt5, symbol)
        print(f"Using broker symbol '{name}'")
        chunks, t0, end = [], pd.Timestamp(start), pd.Timestamp.now("UTC").tz_localize(None) + pd.Timedelta(days=1)
        while t0 < end:                       # yearly chunks: MT5 refuses very large single requests
            t1 = min(t0 + pd.DateOffset(years=1), end)
            r = mt5.copy_rates_range(name, tf, t0.to_pydatetime(), t1.to_pydatetime())
            n = 0 if r is None else len(r)
            print(f"  {t0.date()} → {t1.date()}: {n} bars" + ("" if n else f"  (MT5: {mt5.last_error()})"))
            if n:
                chunks.append(pd.DataFrame(r))
            t0 = t1
        if not chunks:                        # fallback: whatever the terminal already has, newest first
            r = mt5.copy_rates_from_pos(name, tf, 0, 500_000)
            if r is not None and len(r):
                chunks.append(pd.DataFrame(r))
                print(f"  fallback copy_rates_from_pos: {len(r)} bars")
    finally:
        mt5.shutdown()
    if not chunks:
        raise SystemExit("No bars returned. In MT5: Tools > Options > Charts > 'Max. bars in chart' = Unlimited, "
                         "restart MT5, open an XAUUSD M15 chart, press Home a few times to load history, then retry.")
    df = pd.concat(chunks).drop_duplicates("time").sort_values("time")
    df["time"] = server_to_utc(pd.to_datetime(df["time"], unit="s"), server_tz)
    out = _path(out_symbol, timeframe)
    out.parent.mkdir(parents=True, exist_ok=True)
    df[["time", "open", "high", "low", "close", "spread"]].to_csv(out, index=False)
    print(f"Saved {len(df)} bars, {df['time'].iloc[0]} → {df['time'].iloc[-1]} UTC (server clock: {server_tz})")
    return out


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--symbol", default="XAUUSD", help="broker symbol; common variants are tried automatically")
    e.add_argument("--timeframe", default="M15")
    e.add_argument("--start", default="2019-01-01")
    e.add_argument("--server-tz", default="nyclose", help="'nyclose' (UTC+2/+3, default) or fixed hours e.g. 2")
    a = ap.parse_args()
    print(export_mt5(a.symbol, a.timeframe, a.start, a.server_tz))
