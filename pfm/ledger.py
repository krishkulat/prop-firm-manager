"""The $250 account reserve. Only changes through owner-confirmed events (/bought, /reject, /paid, breach)."""
from __future__ import annotations

import json
from datetime import date

from . import ROOT
from .config import business

PATH = ROOT / "ledger/ledger.json"


def load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def save(l: dict):
    PATH.write_text(json.dumps(l, indent=2), encoding="utf-8")


def balances(l: dict | None = None) -> dict:
    l = l or load()
    out = {"reserved": 0, "locked": 0, "free": 0, "pending": 0}
    for ln in l["lines"]:
        out[ln["status"]] = out.get(ln["status"], 0) + ln["amount"]
    out["spent"] = sum(s["amount"] for s in l["spent"])
    out["payouts"] = sum(p["amount"] for p in l["payouts"])
    return out


def reserve(request_id: str, price: float, retry: bool = False) -> str:
    """Earmark money for a purchase request. Returns the line id used. Raises if it doesn't fit."""
    l = load()
    biz = business()
    if biz["business"]["halted"]:
        raise RuntimeError("business is halted (stop-loss); no purchases")
    lines = {ln["id"]: ln for ln in l["lines"]}
    if retry:
        ln = lines.get("retry")
        if not ln or ln["status"] != "free":
            raise RuntimeError("retry line not unlocked (needs a recorded breach)")
        candidates = [ln]
    else:
        candidates = [x for x in l["lines"] if x["status"] in ("reserved", "free") and x["id"] != "retry"
                      and x["request_id"] is None]
    for ln in candidates:
        if ln["amount"] >= price:
            rest = round(ln["amount"] - price, 2)
            ln.update(amount=price, status="pending", request_id=request_id)
            if rest > 0:
                l["lines"].append({"id": f"rest-{request_id}", "label": "Unallocated (change)", "amount": rest,
                                   "status": "free", "request_id": None})
            save(l)
            return ln["id"]
    raise RuntimeError(f"${price} does not fit any available ledger line: {balances(l)}")


def confirm_bought(request_id: str, account_label: str, login_last4: str = ""):
    l = load()
    ln = next(x for x in l["lines"] if x["request_id"] == request_id)
    l["lines"].remove(ln)
    l["spent"].append({"request_id": request_id, "amount": ln["amount"], "account": account_label,
                       "login_last4": login_last4, "date": str(date.today())})
    l.setdefault("accounts", []).append({"label": account_label, "request_id": request_id, "status": "evaluation",
                                         "login_last4": login_last4, "bought": str(date.today())})
    save(l)


def release(request_id: str):
    l = load()
    for ln in l["lines"]:
        if ln["request_id"] == request_id:
            ln.update(status="free" if ln["id"] != "acct1" else "reserved", request_id=None)
    save(l)


def record_breach(account_label: str) -> dict:
    l = load()
    l["breached_attempts"] = l.get("breached_attempts", 0) + 1
    for a in l.get("accounts", []):
        if a["label"] == account_label:
            a["status"] = "breached"
    for ln in l["lines"]:
        if ln["id"] == "retry" and ln["status"] == "locked":
            ln["status"] = "free"
    save(l)
    return stop_loss_status(l)


def record_payout(account_label: str, amount: float) -> dict:
    """Applies config reinvestment policy. Returns the split."""
    l = load()
    rp = business()["reinvestment"]
    first = not l["payouts"]
    l["payouts"].append({"account": account_label, "amount": amount, "date": str(date.today())})
    split = {}
    if first:
        tax = amount * rp["first_payout"]["tax_reserve_pct"] / 100
        seed = min(rp["first_payout"]["return_seed_usd"], amount - tax)
        split = {"tax_reserve": round(tax, 2), "seed_returned_to_owner": round(seed, 2),
                 "to_reserve": round(amount - tax - seed, 2)}
    else:
        a = rp["after"]
        split = {"new_challenges": round(amount * a["new_challenges_pct"] / 100, 2),
                 "reserve": round(amount * a["reserve_pct"] / 100, 2),
                 "owner": round(amount * a["owner_pct"] / 100, 2)}
    add = split.get("to_reserve", 0) + split.get("new_challenges", 0) + split.get("reserve", 0)
    if add > 0:
        l["lines"].append({"id": f"payout-{len(l['payouts'])}", "label": "From payout", "amount": add,
                           "status": "free", "request_id": None})
        l["total"] = round(l["total"] + add, 2)
    save(l)
    return split


def stop_loss_status(l: dict | None = None) -> dict:
    l = l or load()
    sl = business()["stop_loss"]
    funded = any(a.get("status") == "funded" for a in l.get("accounts", []))
    spent = sum(s["amount"] for s in l["spent"])
    reasons = []
    if l.get("breached_attempts", 0) >= sl["max_breached_attempts"]:
        reasons.append(f"{l['breached_attempts']} breached attempts")
    if not funded and spent >= sl["max_spend_without_funded_usd"]:
        reasons.append(f"${spent} spent without a funded account")
    if not funded and str(date.today()) > str(sl["strategy_search_deadline"]) and not l.get("accounts"):
        reasons.append("strategy search deadline passed")
    return {"hit": bool(reasons), "reasons": reasons}
