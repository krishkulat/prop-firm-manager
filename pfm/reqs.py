"""Owner requests: purchase, deploy, payout. Each is a YAML file in requests/ plus a Telegram message.

CLI (used by the Capital and Ops agents):
  python -m pfm.reqs purchase --product the5ers/hs50k_10d --strategy A --reason "..." [--retry]
  python -m pfm.reqs deploy --account the5ers-hs50k_10d-P-001 --release A-v1.0 [--kind new|update|remove]
  python -m pfm.reqs payout --account <label> --amount 1200
  python -m pfm.reqs list
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime

import yaml

from . import ROOT, config, ledger, notify

DIR = ROOT / "requests"
PREFIX = {"purchase": "P", "deploy": "D", "payout": "W"}


def _next_id(kind: str) -> str:
    DIR.mkdir(exist_ok=True)
    n = len(list(DIR.glob(f"{PREFIX[kind]}-*.yaml"))) + 1
    return f"{PREFIX[kind]}-{n:03d}"


def _save(r: dict):
    (DIR / f"{r['id']}.yaml").write_text(yaml.safe_dump(r, sort_keys=False), encoding="utf-8")


def load(rid: str) -> dict:
    return yaml.safe_load((DIR / f"{rid}.yaml").read_text(encoding="utf-8"))


def list_open() -> list[dict]:
    return [r for r in (yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("*-*.yaml")))
            if r.get("status") == "open"]


def close(rid: str, status: str, note: str = "") -> dict:
    r = load(rid)
    if r["status"] != "open":
        raise RuntimeError(f"{rid} is already {r['status']}")
    r.update(status=status, closed=datetime.now().isoformat(timespec="seconds"), note=note)
    _save(r)
    return r


def purchase(product_key: str, strategy: str, reason: str, retry: bool = False, evidence: str = "") -> dict:
    p = config.firm_product(product_key)
    rid = _next_id("purchase")
    line = ledger.reserve(rid, p["price_usd"], retry=retry)
    b = ledger.balances()
    risk = config.risk_profile(f"{p['firm'].lower()}_{product_key.split('/')[1]}")
    label = f"{product_key.replace('/', '-')}-{rid}"
    text = (f"PURCHASE REQUEST  {rid}\n"
            f"Firm / product : {p['firm']} {p['name']}\n"
            f"Price          : ${p['price_usd']}  (from ledger line '{line}'; free after: ${b['free']}, locked: ${b['locked']})\n"
            f"Why            : {reason}\n"
            + (f"Evidence       : {evidence}\n" if evidence else "") +
            f"Bot assigned   : strategy {strategy}\n"
            f"Rules mapped   : daily {p['daily_loss_pct']}% -> bot stop {risk['daily_stop_pct']}% | "
            f"max loss {p['max_loss_pct']}% -> kill at {risk['kill_dd_pct']}%\n"
            f"Account label  : {label}\n"
            f"Reply          : /bought {rid} <account login>   or   /reject {rid} <reason>")
    r = {"id": rid, "kind": "purchase", "status": "open", "created": datetime.now().isoformat(timespec="seconds"),
         "product": product_key, "price_usd": p["price_usd"], "strategy": strategy, "retry": retry,
         "account_label": label, "ledger_line": line, "text": text}
    _save(r)
    notify.send(text)
    return r


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "<build first>"


def deploy(account: str, release: str, kind: str = "new") -> dict:
    rid = _next_id("deploy")
    rel = ROOT / "releases" / release
    ea = next(rel.glob("*.mq5"), None) if rel.exists() else None
    st = next(rel.glob("*.set"), None) if rel.exists() else None
    if kind == "remove":
        steps = "1) remove the EA from the chart  2) confirm no open positions  3) turn off Algo Trading"
    else:
        steps = ("1) copy the .mq5 to MQL5/Experts and compile in MetaEditor (or copy the .ex5)\n"
                 "                 2) open XAUUSD M15 chart  3) attach EA  4) load the .set file\n"
                 "                 5) turn on Algo Trading  6) Experts tab shows 'PFM risk engine ready'")
    text = (f"DEPLOY REQUEST  {rid}   ({kind})\n"
            f"Account        : {account}\n"
            f"Release        : {release}\n"
            f"EA source      : {ea.name if ea else '?'}   SHA-256 {(_sha(ea) if ea else '?')[:16]}…\n"
            f"Settings file  : {st.name if st else '?'}   SHA-256 {(_sha(st) if st else '?')[:16]}…\n"
            f"Package        : releases/{release}/ in the repo (see DEPLOY.md)\n"
            f"Steps          : {steps}\n"
            f"Check          : monitor confirms the heartbeat within 10 minutes\n"
            f"Reply          : /deployed {rid}   or   /reject {rid} <reason>")
    r = {"id": rid, "kind": "deploy", "status": "open", "created": datetime.now().isoformat(timespec="seconds"),
         "account_label": account, "release": release, "deploy_kind": kind, "text": text}
    _save(r)
    notify.send(text)
    return r


def payout(account: str, amount: float) -> dict:
    rid = _next_id("payout")
    text = (f"PAYOUT READY  {rid}\n"
            f"Account        : {account}\n"
            f"Eligible amount: ${amount} (check exact figure on The5ers Hub)\n"
            f"Action         : request the payout on the Hub to your bank\n"
            f"Reply          : /paid {rid} <amount received>   or   /reject {rid} <reason>")
    r = {"id": rid, "kind": "payout", "status": "open", "created": datetime.now().isoformat(timespec="seconds"),
         "account_label": account, "amount": amount, "text": text}
    _save(r)
    notify.send(text)
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("purchase"); a.add_argument("--product", required=True); a.add_argument("--strategy", required=True)
    a.add_argument("--reason", required=True); a.add_argument("--evidence", default=""); a.add_argument("--retry", action="store_true")
    d = sub.add_parser("deploy"); d.add_argument("--account", required=True); d.add_argument("--release", required=True)
    d.add_argument("--kind", default="new", choices=["new", "update", "remove"])
    w = sub.add_parser("payout"); w.add_argument("--account", required=True); w.add_argument("--amount", type=float, required=True)
    sub.add_parser("list")
    x = ap.parse_args()
    if x.cmd == "purchase":
        print(purchase(x.product, x.strategy, x.reason, x.retry, x.evidence)["id"])
    elif x.cmd == "deploy":
        print(deploy(x.account, x.release, x.kind)["id"])
    elif x.cmd == "payout":
        print(payout(x.account, x.amount)["id"])
    else:
        for r in list_open():
            print(r["id"], r["kind"], r["created"])
