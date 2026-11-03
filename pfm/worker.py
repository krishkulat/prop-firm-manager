"""Job worker for the research machine (your PC now, the research VPS later).

Loop: git pull → run oldest ticket in queue/pending → write results/<job_id>/ → log trials → move ticket →
commit + push. Also polls Telegram for owner replies each cycle.

Run:  python -m pfm.worker            (loop forever)
      python -m pfm.worker --once     (one ticket, for testing)
      python -m pfm.worker --no-git   (local only)
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import ROOT, backtest, config, data, propsim
from .metrics import check_gate, deflated_sharpe, summarize
from .walkforward import run_one, sweep, walkforward

PENDING, DONE, FAILED = ROOT / "queue/pending", ROOT / "queue/done", ROOT / "queue/failed"
RESULTS = ROOT / "results"
TRIALS = RESULTS / "trials.csv"


def log(msg: str):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def git(*args, check=False):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)


def load_strategy(key: str):
    reg = config.registry()[key]
    mod = importlib.import_module(reg["module"])
    cls = next(v for v in vars(mod).values() if isinstance(v, type) and getattr(v, "name", None) == key)
    return cls(), reg


def load_news() -> list[pd.Timestamp]:
    # column time (UTC) of high-impact USD events; data/news.csv (git-ignored) wins over the repo calendar
    p = ROOT / "data/news.csv"
    if not p.exists():
        p = ROOT / "research/news/usd_high_impact.csv"
    if not p.exists():
        return []
    return list(pd.to_datetime(pd.read_csv(p)["time"], utc=True))


def log_trials(job: dict, rows: list[dict]):
    TRIALS.parent.mkdir(parents=True, exist_ok=True)
    new = not TRIALS.exists()
    with open(TRIALS, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "job_id", "kind", "strategy", "hypothesis", "params", "trades", "pf", "max_dd_pct", "sharpe"])
        for r in rows:
            w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), job["job_id"], job["kind"],
                        job["strategy"], job.get("hypothesis", ""), json.dumps(r.get("params", {})),
                        r.get("trades"), r.get("pf"), r.get("max_dd_pct"), r.get("sharpe")])


def trials_for(hypothesis: str) -> int:
    if not TRIALS.exists():
        return 0
    df = pd.read_csv(TRIALS)
    return int((df["hypothesis"] == hypothesis).sum())


def daily_from_trades(trades: pd.DataFrame, initial: float) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["date", "equity", "low"])
    t = trades.assign(date=pd.to_datetime(trades["exit_time"]).dt.tz_convert("Asia/Kolkata").dt.date)
    g = t.groupby("date")["pnl"].sum().cumsum() + initial
    return pd.DataFrame({"date": g.index, "equity": g.values, "low": g.values})


def _bars(job: dict) -> pd.DataFrame:
    d = job.get("data", {})
    split = "holdout" if job["kind"] == "holdout" else "research"
    if d.get("synthetic"):
        df = data.synthetic(days=d.get("days", 600))
        cut = data.holdout_start(df)
        return df[df.index >= cut] if split == "holdout" else df[df.index < cut]
    return data.load(d.get("symbol", "XAUUSD"), d.get("timeframe", "M15"), split=split)


def run_job(job: dict) -> dict:
    biz = config.business()
    costs = biz["research"]["costs"]
    slip = costs["slippage_points"]
    risk = config.risk_profile(job.get("risk_profile", "the5ers_hs50k_10d"))
    # Research mode: measure the edge over the whole period. The account-level kill switch and the drawdown
    # throttle belong to the challenge (tested in propsim); with them on, a backtest stops at the first 6% DD.
    research_risk = {**risk, "kill_dd_pct": 1e9, "throttle_dd_pct": 1e9}
    gates = biz["gates"]
    out = RESULTS / job["job_id"]
    out.mkdir(parents=True, exist_ok=True)
    news = load_news()
    kind = job["kind"]

    if kind == "holdout" and job.get("requested_by") != "validation":
        raise PermissionError("holdout jobs may only be requested by the validation agent")

    strat, reg = load_strategy(job["strategy"])
    params = {**strat.default_params, **job.get("params", {})}
    summary: dict = {"job_id": job["job_id"], "kind": kind, "strategy": job["strategy"], "params": params,
                     "news_calendar_loaded": bool(news)}

    if kind in ("backtest", "holdout"):
        bars = _bars(job)
        res, s = run_one(strat, bars, params, research_risk, slip, news)
        res.trades.to_csv(out / "trades.csv", index=False)
        res.daily.to_csv(out / "equity.csv", index=False)
        s["rejections"] = res.rejections
        # stress: +50% slippage (not logged as a trial)
        _, s_stress = run_one(strat, bars, params, research_risk, slip * 1.5, news)
        s["stress_slip_pf"] = s_stress["pf"]
        # stress: +50% spread (reporting only, not part of any gate)
        _, s_spread = run_one(strat, bars.assign(spread=bars["spread"] * 1.5), params, research_risk, slip, news)
        s["stress_spread_pf"] = s_spread["pf"]
        if kind == "holdout":
            rets = np.diff(np.r_[res.initial, res.daily["equity"].to_numpy()]) / res.initial
            s["deflated_sharpe"] = round(deflated_sharpe(rets, trials_for(job.get("hypothesis", ""))), 4)
            ref = job.get("in_sample_ref", {"max_dd_pct": 0})
            ok, fails = check_gate("holdout", s, gates, ref)
        else:
            ok, fails = check_gate("backtested", s, gates)
        summary.update(s, gate={"name": "holdout" if kind == "holdout" else "backtested", "pass": ok, "fails": fails})
        log_trials(job, [{"params": params, **s}])

    elif kind == "sweep":
        bars = _bars(job)
        used = trials_for(job.get("hypothesis", ""))
        cap = biz["research"]["max_trials_per_hypothesis"] - used
        table = sweep(strat, bars, job["grid"], research_risk, slip, max_trials=cap, news=news)
        table.to_csv(out / "sweep.csv", index=False)
        keys = list(job["grid"])
        log_trials(job, [{"params": {k: r[k] for k in keys}, **r} for r in table.to_dict("records")])
        best = table.sort_values("pf", ascending=False).iloc[0].to_dict()
        summary.update(combos=len(table), trials_used_before=used, best=best,
                       neighbours_profitable_share=round(float((table.pf > 1.0).mean()), 3))

    elif kind == "walkforward":
        bars = _bars(job)
        wf = job.get("walkforward", {})
        trades, chosen, _ = walkforward(strat, bars, job["grid"], research_risk, slip,
                                        wf.get("train_months", 24), wf.get("test_months", 6), news=news)
        chosen.to_csv(out / "windows.csv", index=False)
        trades.to_csv(out / "trades.csv", index=False)
        s = summarize(trades, daily_from_trades(trades, risk["account_size"]), risk["account_size"])
        _, s_is = run_one(strat, bars, params, research_risk, slip, news)
        ok, fails = check_gate("walkforward", s, gates, s_is)
        summary.update(oos=s, in_sample=s_is, windows=len(chosen), gate={"name": "walkforward", "pass": ok, "fails": fails})
        log_trials(job, [{"params": r, **r} for r in chosen.to_dict("records")])

    elif kind == "propsim":
        ps = job["propsim"]
        src = RESULTS / ps["source_job"] / "trades.csv"
        trades = pd.read_csv(src, parse_dates=["entry_time", "exit_time"])
        product = config.firm_product(ps["product"])
        r = propsim.simulate(trades, product, risk, runs=ps.get("runs", gates["propsim"]["runs"]))
        ok, fails = check_gate("propsim", r, gates)
        summary.update(r, product=ps["product"], gate={"name": "propsim", "pass": ok, "fails": fails})
    else:
        raise ValueError(f"unknown job kind {kind}")

    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    return summary


def next_ticket() -> Path | None:
    tickets = sorted(PENDING.glob("*.yaml"))
    return tickets[0] if tickets else None


def process_one(use_git: bool) -> bool:
    t = next_ticket()
    if t is None:
        return False
    job = yaml.safe_load(t.read_text(encoding="utf-8"))
    log(f"running {job['job_id']} ({job['kind']} {job['strategy']})")
    try:
        s = run_job(job)
        shutil.move(str(t), DONE / t.name)
        gate = s.get("gate", {})
        msg = f"done {job['job_id']}" + (f" gate {gate.get('name')}: {'PASS' if gate.get('pass') else 'FAIL'}" if gate else "")
        log(msg)
    except Exception as e:  # noqa: BLE001 - record any failure in the ticket's result folder
        out = RESULTS / job["job_id"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        shutil.move(str(t), FAILED / t.name)
        msg = f"FAILED {job['job_id']}: {e}"
        log(msg)
    if use_git:
        git("add", "-A")
        git("commit", "-m", f"[worker] {msg}")
        p = git("push")
        if p.returncode != 0:
            log(f"push failed: {p.stderr.strip()[:200]}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    use_git = not a.no_git
    for d in (PENDING, DONE, FAILED, RESULTS):
        d.mkdir(parents=True, exist_ok=True)
    log("worker started")
    while True:
        if use_git:
            r = git("pull", "--rebase", "--autostash")
            if r.returncode != 0:
                log(f"pull failed: {r.stderr.strip()[:200]}")
        try:
            from . import notify
            notify.poll_replies()
        except Exception as e:  # noqa: BLE001 - Telegram is optional; never stop the worker for it
            log(f"telegram poll skipped: {e}")
        worked = process_one(use_git)
        if a.once:
            break
        if not worked:
            time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
