"""Release packaging: generate the EA .set file from config/risk/*.yaml and build releases/<tag>/.

  python -m pfm.release make-set --profile the5ers_hs50k_10d --strategy A --step-target 10
  python -m pfm.release package --strategy A --version 1.0 --profile the5ers_hs50k_10d --ea GoldBreakout_A
"""
from __future__ import annotations

import argparse
import hashlib
import shutil

import yaml

from . import ROOT, config

# risk yaml key → EA input name
MAP = {"account_size": "InpAccountSize", "risk_per_trade_pct": "InpRiskPerTradePct",
       "throttle_dd_pct": "InpThrottleDDPct", "throttle_risk_pct": "InpThrottleRiskPct",
       "daily_stop_pct": "InpDailyStopPct", "kill_dd_pct": "InpKillDDPct",
       "daily_profit_stop_pct": "InpDailyProfitStopPct", "max_day_share_of_target": "InpMaxDayShareOfTarget",
       "max_open_positions": "InpMaxOpenPositions", "max_open_risk_pct": "InpMaxOpenRiskPct",
       "max_trades_per_day": "InpMaxTradesPerDay", "entry_start_ist": "InpEntryStartIST",
       "entry_end_ist": "InpEntryEndIST", "flat_by_ist": "InpFlatByIST",
       "news_flat_before_min": "InpNewsFlatBeforeMin", "news_resume_after_min": "InpNewsResumeAfterMin",
       "min_hold_seconds": "InpMinHoldSeconds", "spread_max_ratio": "InpSpreadMaxRatio",
       "stale_feed_seconds": "InpStaleFeedSeconds"}
STRAT_MAP = {"rr": "InpRR", "stop_atr": "InpStopATR", "min_range_atr": "InpMinRangeATR", "max_range_atr": "InpMaxRangeATR",
             "asia_rise_atr": "InpAsiaRiseATR", "exit_et": "InpExitET"}


def make_set(profile: str, strategy: str, step_target: float, magic: int = 1010) -> str:
    r = config.risk_profile(profile)
    reg = config.registry()[strategy]
    pdir = ROOT / "strategies" / reg["module"].split(".")[1]
    params = yaml.safe_load((pdir / "params.yaml").read_text(encoding="utf-8"))
    frozen = reg.get("frozen_params") or params["default"]
    lines = [f"; PFM settings — profile {profile}, strategy {strategy} v{reg['version']}. Generated; do not edit by hand."]
    for k, name in MAP.items():
        lines.append(f"{name}={r[k]}")
    lines += [f"InpStepTargetPct={step_target}", f"InpMagic={magic}", "InpUseNewsFilter=true"]
    for k, name in STRAT_MAP.items():
        if k in frozen:
            lines.append(f"{name}={frozen[k]}")
    return "\n".join(lines) + "\n"


def sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def package(strategy: str, version: str, profile: str, ea: str, step_target: float = 10.0):
    tag = f"{strategy}-v{version}"
    out = ROOT / "releases" / tag
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "mql5/Experts" / f"{ea}.mq5", out / f"{ea}.mq5")
    shutil.copy(ROOT / "mql5/Include/PFM/RiskEngine.mqh", out / "RiskEngine.mqh")
    setf = out / f"{strategy}-v{version}_{profile}.set"
    setf.write_text(make_set(profile, strategy, step_target), encoding="utf-8")
    sums = {p.name: sha(p) for p in sorted(out.iterdir()) if p.suffix in (".mq5", ".mqh", ".set")}
    (out / "SHA256SUMS.txt").write_text("".join(f"{v}  {k}\n" for k, v in sums.items()), encoding="utf-8")
    (out / "DEPLOY.md").write_text(f"""# Deploy {tag} ({profile})

1. On the live VPS, copy `RiskEngine.mqh` to `MQL5/Include/PFM/` and `{ea}.mq5` to `MQL5/Experts/`.
2. Open MetaEditor, compile `{ea}.mq5` (0 errors).
3. In MT5 log in to the prop account. Open an **XAUUSD M15** chart.
4. Drag `{ea}` onto the chart → Inputs tab → **Load** → `{setf.name}`.
5. Tick "Allow Algo Trading", press OK, and turn on the Algo Trading button.
6. Experts tab must show `PFM risk engine ready | size=...`. Check the values match the request.
7. Tools → Options → Expert Advisors: allow WebRequest is NOT needed.
8. Start the monitor: `python -m pfm.monitor --account <label>`.
9. Reply `/deployed <request id>` on Telegram.

Step 2 of the challenge: change `InpStepTargetPct` to 5. Funded: set it to 0.
""", encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make-set"); m.add_argument("--profile", required=True); m.add_argument("--strategy", required=True)
    m.add_argument("--step-target", type=float, default=10.0)
    p = sub.add_parser("package"); p.add_argument("--strategy", required=True); p.add_argument("--version", required=True)
    p.add_argument("--profile", required=True); p.add_argument("--ea", required=True); p.add_argument("--step-target", type=float, default=10.0)
    a = ap.parse_args()
    if a.cmd == "make-set":
        print(make_set(a.profile, a.strategy, a.step_target))
    else:
        print(package(a.strategy, a.version, a.profile, a.ea, a.step_target))
