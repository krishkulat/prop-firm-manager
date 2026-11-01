"""Prop-challenge simulator.

Replays a strategy's trade list (from a backtest) against a firm product's exact rules, many times from random
start points, and reports pass / breach / unfinished rates.

Method: trades are re-sized in R (risk units) with the product's risk profile, in their original order and
spacing. Each trade's adverse excursion (mae_r) is used to test intra-trade limit breaches. Trades in one day
are applied in sequence. Assumes trades don't overlap (true for one-trade-per-day strategies; for others treat
results as optimistic).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .risk import IST


def simulate(trades: pd.DataFrame, product: dict, risk_cfg: dict, runs: int = 500, seed: int = 1,
             max_days: int = 180) -> dict:
    if trades.empty:
        return {"runs": 0, "pass_rate": 0.0, "breach_rate": 0.0, "unfinished_rate": 1.0, "median_days_to_pass": None}
    t = trades.sort_values("entry_time").reset_index(drop=True)
    days = pd.to_datetime(t["entry_time"]).dt.tz_convert(IST).dt.normalize()
    t = t.assign(day=days)
    rng = np.random.default_rng(seed)
    init = float(product["account_size"])
    starts = rng.integers(0, max(len(t) - 20, 1), size=runs)
    outcomes, days_to_pass, breach_reasons = [], [], {}

    for s in starts:
        seq = t.iloc[s:]
        first_day = seq["day"].iloc[0]
        step_i, eq, step_days = 0, init, set()
        out, reason = "unfinished", None
        cur_day, day_start, day_closed, locked = None, eq, 0.0, False
        last_trade_day = first_day
        for _, tr in seq.iterrows():
            if (tr.day - first_day).days > max_days:
                break
            if (tr.day - last_trade_day).days > product.get("inactivity_days", 30):
                out, reason = "breach", "inactivity"; break
            if tr.day != cur_day:
                if cur_day is not None and day_closed >= init * product["profitable_day_min_pct"] / 100:
                    step_days.add(cur_day)
                cur_day, day_start, day_closed, locked = tr.day, eq, 0.0, False
            if locked:
                continue
            dd = (init - eq) / init * 100
            rp = risk_cfg["throttle_risk_pct"] if dd >= risk_cfg["throttle_dd_pct"] else risk_cfg["risk_per_trade_pct"]
            risk = init * rp / 100
            risk = min(risk, init * risk_cfg["daily_stop_pct"] / 100 - (day_start - eq),
                       init * risk_cfg["kill_dd_pct"] / 100 - (init - eq))
            if risk <= 0:
                locked = True; continue
            low = eq - max(tr.mae_r, 0) * risk
            if (day_start - low) / init * 100 >= product["daily_loss_pct"]:
                out, reason = "breach", "daily_loss"; break
            if (init - low) / init * 100 >= product["max_loss_pct"]:
                out, reason = "breach", "max_loss"; break
            pnl = tr.r * risk
            eq += pnl
            day_closed += pnl
            last_trade_day = tr.day
            if (init - eq) / init * 100 >= risk_cfg["kill_dd_pct"]:
                out, reason = "killed", "internal_kill"; break
            if (day_start - eq) / init * 100 >= risk_cfg["daily_stop_pct"] or \
               (eq - day_start) / init * 100 >= risk_cfg["daily_profit_stop_pct"]:
                locked = True
            step = product["steps"][step_i]
            cand_days = step_days | ({cur_day} if day_closed >= init * product["profitable_day_min_pct"] / 100 else set())
            if (eq - init) / init * 100 >= step["target_pct"] and len(cand_days) >= step["min_profitable_days"]:
                step_i += 1
                if step_i == len(product["steps"]):
                    out = "pass"; days_to_pass.append((tr.day - first_day).days); break
                eq, step_days, locked = init, set(), True    # next step starts fresh next day
                day_start, day_closed = eq, 0.0
        outcomes.append(out)
        if reason:
            breach_reasons[reason] = breach_reasons.get(reason, 0) + 1

    o = pd.Series(outcomes)
    return {"runs": runs,
            "pass_rate": round(float((o == "pass").mean()), 3),
            "breach_rate": round(float(o.isin(["breach", "killed"]).mean()), 3),
            "unfinished_rate": round(float((o == "unfinished").mean()), 3),
            "median_days_to_pass": float(np.median(days_to_pass)) if days_to_pass else None,
            "fail_reasons": breach_reasons}
