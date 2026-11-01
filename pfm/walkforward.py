"""Grid sweep and rolling walk-forward."""
from __future__ import annotations

import itertools

import pandas as pd

from . import backtest
from .metrics import summarize


def grid(spec: dict) -> list[dict]:
    keys = list(spec)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(spec[k] for k in keys))]


def run_one(strategy, bars, params, risk_cfg, slippage_points, news=None):
    sigs = strategy.generate_signals(bars, params)
    res = backtest.run(bars, sigs, risk_cfg, slippage_points=slippage_points, news_times_utc=news)
    return res, summarize(res.trades, res.daily, res.initial)


def sweep(strategy, bars, spec, risk_cfg, slippage_points, max_trials: int, news=None):
    combos = grid(spec)
    if len(combos) > max_trials:
        raise ValueError(f"{len(combos)} combos > max_trials_per_hypothesis {max_trials}")
    rows = []
    for p in combos:
        _, s = run_one(strategy, bars, p, risk_cfg, slippage_points, news)
        rows.append({**p, **{k: s[k] for k in ("trades", "pf", "win_rate", "net_pct", "max_dd_pct", "sharpe")}})
    return pd.DataFrame(rows)


def _score(row, min_trades):
    return row["pf"] if row["trades"] >= min_trades else -1


def walkforward(strategy, bars, spec, risk_cfg, slippage_points, train_months=24, test_months=6,
                min_trades_train=60, news=None):
    start, end = bars.index.min(), bars.index.max()
    windows, oos_trades, chosen = [], [], []
    t0 = start
    while True:
        tr_end = t0 + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if tr_end >= end:
            break
        train, test = bars[(bars.index >= t0) & (bars.index < tr_end)], bars[(bars.index >= tr_end) & (bars.index < te_end)]
        if len(test) < 500:
            break
        sw = sweep(strategy, train, spec, risk_cfg, slippage_points, max_trials=10**6, news=news)
        sw["score"] = sw.apply(_score, axis=1, min_trades=min_trades_train)
        best = sw.sort_values("score", ascending=False).iloc[0]
        params = {k: best[k] for k in spec}
        res, s = run_one(strategy, test, params, risk_cfg, slippage_points, news)
        oos_trades.append(res.trades)
        chosen.append({"train_start": str(t0.date()), "test_start": str(tr_end.date()), **params,
                       "train_pf": best["pf"], "test_pf": s["pf"], "test_trades": s["trades"]})
        windows.append(res)
        t0 = t0 + pd.DateOffset(months=test_months)
    trades = pd.concat(oos_trades, ignore_index=True) if oos_trades else pd.DataFrame()
    return trades, pd.DataFrame(chosen), windows
