"""Live monitor — runs on the LIVE VPS next to MT5. Plain script, no AI.

Every 60 s: read account state from MT5 (MetaTrader5 package) and the EA heartbeat file, compute distance to
firm limits, write results/live/<label>/status.json, alert the owner on Telegram, and honour the kill flag.
It pushes status to the repo so agents can read it; it never pulls code or settings from agents.

  python -m pfm.monitor --account the5ers-hs50k_10d-P-001 --profile the5ers_hs50k_10d --product the5ers/hs50k_10d
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from . import ROOT, config, notify


def evaluate(equity: float, day_start: float, product: dict, risk: dict) -> dict:
    """Pure function: distances to firm limits and internal limits, in % of initial balance."""
    init = product["account_size"]
    dd = (init - equity) / init * 100
    day = (day_start - equity) / init * 100
    status = {"equity": round(equity, 2), "overall_dd_pct": round(dd, 3), "day_loss_pct": round(day, 3),
              "room_to_firm_daily_pct": round(product["daily_loss_pct"] - day, 3),
              "room_to_firm_max_pct": round(product["max_loss_pct"] - dd, 3),
              "room_to_kill_pct": round(risk["kill_dd_pct"] - dd, 3)}
    alerts = []
    if status["room_to_firm_daily_pct"] <= 1.0:
        alerts.append(f"within {status['room_to_firm_daily_pct']}% of firm DAILY limit")
    if status["room_to_firm_max_pct"] <= 1.0:
        alerts.append(f"within {status['room_to_firm_max_pct']}% of firm MAX loss")
    if day >= risk["daily_stop_pct"]:
        alerts.append("internal daily stop reached (EA should be flat)")
    status["alerts"] = alerts
    return status


def _common_files() -> Path:  # pragma: no cover - Windows only
    return Path(os.environ.get("APPDATA", "")) / "MetaQuotes/Terminal/Common/Files"


def main():  # pragma: no cover - needs MT5
    import MetaTrader5 as mt5  # type: ignore
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", required=True)
    ap.add_argument("--profile", default="the5ers_hs50k_10d")
    ap.add_argument("--product", default="the5ers/hs50k_10d")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--push-every", type=int, default=15, help="minutes between git pushes")
    a = ap.parse_args()
    product, risk = config.firm_product(a.product), config.risk_profile(a.profile)
    out = ROOT / "results/live" / a.account
    out.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed {mt5.last_error()}")
    day_key, day_start, last_push, last_alert = None, None, 0.0, {}
    while True:
        info = mt5.account_info()
        now = datetime.now(timezone.utc)
        ist_day = (now.timestamp() + 19800) // 86400
        if info is None:
            notify.send(f"MONITOR {a.account}: MT5 not connected"); time.sleep(a.interval); continue
        if ist_day != day_key:
            day_key, day_start = ist_day, max(info.equity, info.balance)
        s = evaluate(info.equity, day_start, product, risk)
        hb = _common_files() / "PFM_status_A.json"
        s["ea_heartbeat_age_s"] = round(now.timestamp() - hb.stat().st_mtime) if hb.exists() else None
        if s["ea_heartbeat_age_s"] is None or s["ea_heartbeat_age_s"] > 300:
            s["alerts"].append("EA heartbeat missing > 5 min")
        kill_repo = ROOT / "results/live/KILL"
        if kill_repo.exists():
            (_common_files() / "PFM_KILL.flag").write_text("kill", encoding="utf-8")
            s["alerts"].append("KILL flag active")
        s["time_utc"] = now.isoformat(timespec="seconds")
        (out / "status.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
        for al in s["alerts"]:
            if time.time() - last_alert.get(al, 0) > 1800:
                notify.send(f"ALERT {a.account}: {al}\nequity {s['equity']} | DD {s['overall_dd_pct']}% | day {s['day_loss_pct']}%")
                last_alert[al] = time.time()
        if time.time() - last_push > a.push_every * 60:
            subprocess.run(["git", "add", str(out)], cwd=ROOT)
            subprocess.run(["git", "commit", "-m", f"[monitor] {a.account} status"], cwd=ROOT, capture_output=True)
            subprocess.run(["git", "push"], cwd=ROOT, capture_output=True)
            last_push = time.time()
        time.sleep(a.interval)


if __name__ == "__main__":  # pragma: no cover
    main()
