"""Performance metrics, gate checks and the deflated Sharpe ratio."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def summarize(trades: pd.DataFrame, daily: pd.DataFrame, initial: float) -> dict:
    out: dict = {"trades": int(len(trades))}
    if trades.empty:
        return {**out, "pf": 0.0, "win_rate": 0.0, "avg_r": 0.0, "net_pct": 0.0, "max_dd_pct": 0.0,
                "yearly_pct": {}, "worst_year_pct": 0.0, "sharpe": 0.0, "best_month_share": 0.0}
    gp = trades.loc[trades.pnl > 0, "pnl"].sum()
    gl = -trades.loc[trades.pnl < 0, "pnl"].sum()
    eq = daily["equity"].to_numpy()
    lows = daily["low"].to_numpy()
    peak = np.maximum.accumulate(np.r_[initial, eq])[1:]
    dd = ((peak - np.minimum(eq, lows)) / initial * 100).max()
    d = daily.assign(year=pd.to_datetime(daily["date"]).dt.year)
    yearly = {}
    prev = initial
    for y, g in d.groupby("year"):
        end = g["equity"].iloc[-1]
        yearly[int(y)] = round(float((end - prev) / initial * 100), 2)
        prev = end
    rets = np.diff(np.r_[initial, eq]) / initial
    sharpe = float(rets.mean() / rets.std() * math.sqrt(252)) if rets.std() > 0 else 0.0
    t = trades.assign(month=pd.to_datetime(trades["exit_time"]).dt.strftime("%Y-%m"))
    monthly = t.groupby("month")["pnl"].sum()
    net = trades.pnl.sum()
    best_share = float(monthly.max() / net) if net > 0 else 0.0
    return {**out,
            "pf": round(float(gp / gl), 3) if gl > 0 else float("inf"),
            "win_rate": round(float((trades.pnl > 0).mean()), 3),
            "avg_r": round(float(trades.r.mean()), 3),
            "net_pct": round(float(net / initial * 100), 2),
            "max_dd_pct": round(float(dd), 2),
            "yearly_pct": yearly,
            "worst_year_pct": float(min(yearly.values())) if yearly else 0.0,
            "sharpe": round(sharpe, 3),
            "best_month_share": round(best_share, 3),
            "exit_reasons": {k: int(v) for k, v in trades.reason.value_counts().items()}}


def check_gate(name: str, s: dict, gates: dict, ref: dict | None = None) -> tuple[bool, list[str]]:
    g = gates[name]
    fails = []
    if name == "backtested":
        if s["trades"] < g["min_trades"]: fails.append(f"trades {s['trades']} < {g['min_trades']}")
        if s["pf"] < g["min_pf"]: fails.append(f"PF {s['pf']} < {g['min_pf']}")
        if s["max_dd_pct"] > g["max_dd_pct"]: fails.append(f"maxDD {s['max_dd_pct']}% > {g['max_dd_pct']}%")
        if s["worst_year_pct"] < g["worst_year_pct"]: fails.append(f"worst year {s['worst_year_pct']}% < {g['worst_year_pct']}%")
    elif name == "walkforward":
        if s["pf"] < g["min_oos_pf"]: fails.append(f"OOS PF {s['pf']} < {g['min_oos_pf']}")
        if ref and ref["max_dd_pct"] > 0 and s["max_dd_pct"] > g["max_oos_dd_ratio"] * ref["max_dd_pct"]:
            fails.append(f"OOS DD {s['max_dd_pct']}% > {g['max_oos_dd_ratio']}x IS {ref['max_dd_pct']}%")
    elif name == "holdout":
        if s["pf"] < g["min_pf"]: fails.append(f"holdout PF {s['pf']} < {g['min_pf']}")
        if ref and ref["max_dd_pct"] > 0 and s["max_dd_pct"] > g["max_dd_ratio"] * ref["max_dd_pct"]:
            fails.append(f"holdout DD {s['max_dd_pct']}% > {g['max_dd_ratio']}x IS")
        if s.get("deflated_sharpe", 0) <= g["min_deflated_sharpe"]: fails.append("deflated Sharpe ≤ 0")
    elif name == "propsim":
        if s["pass_rate"] < g["min_pass_rate"]: fails.append(f"pass {s['pass_rate']:.0%} < {g['min_pass_rate']:.0%}")
        if s["breach_rate"] > g["max_breach_rate"]: fails.append(f"breach {s['breach_rate']:.0%} > {g['max_breach_rate']:.0%}")
    return (not fails), fails


def _norm_ppf(p: float) -> float:
    # Acklam's approximation, good to ~1e-9 — avoids a scipy dependency
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def deflated_sharpe(returns: np.ndarray, n_trials: int, sr_trials_std: float | None = None) -> float:
    """Bailey & López de Prado (2014). Returns DSR - 0.5 so that > 0 means 'more likely real than not'.

    returns: per-period (daily) returns of the chosen strategy. n_trials: how many configs were tried.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 30 or r.std() == 0:
        return -0.5
    sr = r.mean() / r.std()
    skew = float(((r - r.mean()) ** 3).mean() / r.std() ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std() ** 4)
    sd = sr_trials_std if sr_trials_std is not None else 1 / math.sqrt(n)   # null: SR estimate noise
    n_trials = max(int(n_trials), 1)
    if n_trials > 1:
        em = 0.5772156649
        sr0 = sd * ((1 - em) * _norm_ppf(1 - 1 / n_trials) + em * _norm_ppf(1 - 1 / (n_trials * math.e)))
    else:
        sr0 = 0.0
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    return 0.5 * (1 + math.erf(z / math.sqrt(2))) - 0.5
