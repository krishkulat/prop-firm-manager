"""Telegram: send messages to the owner and read owner replies.

Owner commands (only from TELEGRAM_CHAT_ID):
  /bought <request_id> <login>     account purchased  (only the last 4 digits are stored)
  /deployed <request_id>           bot deployed on the live VPS
  /paid <request_id> <amount>      payout received
  /breached <account_label>        account failed a firm rule
  /funded <account_label>          account passed and is now funded
  /reject <request_id> <reason>    request declined
  /status                          ledger + open requests
  /kill                            sets the kill flag for the live monitor
Without Telegram credentials, messages are printed (dev mode).
"""
from __future__ import annotations

import os

import requests as http

from . import ROOT

OFFSET_FILE = ROOT / "requests/.telegram_offset"


def _env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def send(text: str) -> bool:
    token, chat = _env()
    if not token or not chat:
        print("[telegram:dev]\n" + text)
        return False
    r = http.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  json={"chat_id": chat, "text": f"<pre>{_esc(text)}</pre>", "parse_mode": "HTML"}, timeout=15)
    return r.ok


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def handle(cmd: str) -> str:
    """Apply one owner command. Returns the reply text. Pure enough to unit-test without Telegram."""
    from . import ledger, reqs
    parts = cmd.strip().split()
    if not parts:
        return "empty"
    c, args = parts[0].lower().split("@")[0], parts[1:]
    try:
        if c == "/bought" and len(args) >= 2:
            r = reqs.close(args[0], "done", note=f"bought, login ****{args[1][-4:]}")
            label = r.get("account_label") or f"{r['product'].replace('/', '-')}-{args[0]}"
            ledger.confirm_bought(args[0], label, args[1][-4:])
            return f"OK {args[0]}: recorded purchase as '{label}'. Ops will send a deploy request."
        if c == "/deployed" and args:
            reqs.close(args[0], "done", note="deployed by owner")
            return f"OK {args[0]}: deployed. Watching for the bot heartbeat."
        if c == "/paid" and len(args) >= 2:
            r = reqs.close(args[0], "done", note=f"paid {args[1]}")
            split = ledger.record_payout(r.get("account_label", "?"), float(args[1]))
            return f"OK {args[0]}: payout ${args[1]} recorded. Split: {split}"
        if c == "/breached" and args:
            sl = ledger.record_breach(args[0])
            return f"Recorded breach on {args[0]}. Retry line unlocked." + (f" STOP-LOSS HIT: {sl['reasons']}" if sl["hit"] else "")
        if c == "/funded" and args:
            l = ledger.load()
            for a in l.get("accounts", []):
                if a["label"] == args[0]:
                    a["status"] = "funded"
            ledger.save(l)
            return f"{args[0]} marked funded."
        if c == "/reject" and args:
            reqs.close(args[0], "rejected", note=" ".join(args[1:]))
            ledger.release(args[0])
            return f"OK {args[0]} rejected; any reserved money released."
        if c == "/status":
            b = ledger.balances()
            open_ = [f"{r['id']} {r['kind']}" for r in reqs.list_open()]
            return f"Ledger: {b}\nOpen requests: {open_ or 'none'}"
        if c == "/kill":
            p = ROOT / "results/live/KILL"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("kill requested by owner\n", encoding="utf-8")
            return "KILL flag set. The live monitor will flatten and disable bots on its next check."
    except Exception as e:  # noqa: BLE001 - reply with the error instead of crashing the worker
        return f"Error: {e}"
    return "Unknown command. Use /bought /deployed /paid /breached /funded /reject /status /kill"


def poll_replies():
    token, chat = _env()
    if not token or not chat:
        return
    offset = int(OFFSET_FILE.read_text()) if OFFSET_FILE.exists() else 0
    r = http.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=20)
    for u in r.json().get("result", []):
        offset = u["update_id"] + 1
        msg = u.get("message") or {}
        if str(msg.get("chat", {}).get("id")) != str(chat) or not msg.get("text", "").startswith("/"):
            continue
        send(handle(msg["text"]))
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))
