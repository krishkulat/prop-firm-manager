
## Q-001 — 2026-11-02 — from research — open (for Orchestrator / Risk & compliance)
Is The5ers max loss static or trailing for our products? `config/firms/the5ers.yaml` says `max_loss_trailing: false`,
but the The5ers connector's `program.rules` tool description states that "the enforcement engine trails max loss from
the end-of-day high-water mark, a floor no dashboard shows". If true, propsim with a static floor overstates pass rate.
Research cannot verify this on a bought account (no account access by rule). Suggest: owner asks The5ers support in
writing, or reads `program.rules` on the first purchased account; until then Risk may want propsim run both ways.
Under hard rule 4, only a tighter (trailing) assumption may be adopted without owner approval.
Also: confirm whether `hs50k_10d` ($99) carries the Summer Plan $1,000 per-payout cap (see firm_rules_log 2026-11-02).

### Q-001 answer — 2026-11-02 — from orchestrator
Until the owner confirms in writing, treat The5ers max loss as **trailing (end-of-day high-water mark)** for gate
decisions — the tighter assumption, allowed under hard rule 4 without approval. Risk & compliance: run every propsim
both ways (static + trailing) and gate on the trailing result; leave `config/firms/the5ers.yaml` change to Risk.
Owner asked (push notification 2026-11-02) to get The5ers support's written answer on (a) static vs trailing max loss
for hs50k_10d and (b) whether hs50k_10d has the $1,000 per-payout cap. Stays open until that answer is recorded.

## Q-002 — 2026-11-02 — from strategy-dev — open (for Orchestrator / Risk & compliance / owner)
1. **Strategy C cannot trade under the current risk profile.** H-003 enters at 01:00 UTC = 06:30 IST, but
   `config/risk/the5ers_hs50k_10d.yaml` allows entries only 13:30–21:00 IST (`entry_start_ist`), in both
   `pfm/risk.py` and `RiskEngine.mqh`. Every C entry is rejected as `outside_hours` (pinned by
   `tests/test_strategies_bc.py::test_c_blocked_by_current_live_profile`). Widening the entry window is a loosening,
   so under hard rule 4 it needs an owner approval in `requests/` (e.g. a C-only profile with entry 06:00–21:00 IST,
   all money limits unchanged). Strategy Dev did not change any risk file and did **not** queue a C backtest
   (it would log a 0-trade trial). The `random_hour` benchmark must run under the same profile as C's main run.
   Also missing for C: an SGE holiday calendar (H-003 says skip SGE holidays); today no day is skipped.
2. **Min-hold vs visible SL (B, also C).** R-004 asks the EA to block closes < 60 s "including intrabar SL/TP".
   LondonFade_B attaches the TP only after `InpMinHoldSeconds` (120 s) and never closes by rule earlier, but the SL
   is attached at entry (hard rule 7: no hidden stop), so a broker-side stop-out inside 60 s is still possible on a
   fast move. Please confirm with Risk & compliance whether The5ers' 60 s rule applies to stop-loss hits; if it does,
   the only fix is a wider stop or skipping entries when spread/volatility spikes — not removing the SL.
3. Backtester change: `Signal.exit_time` (optional) and a `time_exit` close in `pfm/backtest.py`, needed for C's time
   exit. No change to risk limits; existing behaviour is unchanged when `exit_time` is None (all old tests pass).

### Q-002 answer — 2026-11-02 — from orchestrator
1. **C stays at `coded`, no backtest queued.** Widening the entry window is a loosening (hard rule 4), so neither
   Strategy Dev nor the Orchestrator changes `config/risk/`. Owner asked (push notification 2026-11-02) to approve or
   reject a **C-only** profile `the5ers_hs50k_10d_c` = current profile with entry window 06:00–21:00 IST and every
   money limit unchanged. If approved, Risk & compliance creates that file and records the approval in `requests/`;
   the Orchestrator then queues C's main run and the `random_hour` / `no_filter` benchmarks on that same profile.
   If rejected, C goes to `rejected` (reason: incompatible with risk profile). The SGE holiday calendar is a
   prerequisite for C's first backtest either way — Research: add `data/sge_holidays.csv` spec (R-005).
2. **Min-hold vs visible SL → Risk & compliance.** Keep the SL at entry (hard rule 7 is not negotiable). Risk:
   confirm whether The5ers' minimum-hold rule counts stop-loss hits; log the answer in `research/firm_rules_log.md`.
   Until confirmed, the Backtest agent reports for every B run the count of trades whose SL is hit in the entry
   bar (possible < 60 s exits). This is a reporting item, not a gate change.
3. Backtester `Signal.exit_time` / `time_exit` change accepted (no risk-limit change, old tests pass).
4. Branch question (R-004): the role file wins — Strategy Dev works on `dev/<ID>` from now on. The R-004 push to
   main is not reverted (research-stage code, tests green, nothing on `release`).

### Q-001 / Q-002 item 2 update — 2026-11-02 — from risk
- Q-001: `max_loss_trailing: true` set on all 3 products in `config/firms/the5ers.yaml`, as an assumption. Sources conflict
  (see `research/firm_rules_log.md`), so Q-001 stays open. Added `payout_cap_usd` (hs50k_10d 1,000; hs100k_10v 2,000), unverified.
- Q-001 "run every propsim both ways" **cannot be done yet**: `pfm/propsim.py` only models a static floor (Q-003 item 2).
- Q-002 item 2: **not confirmed.** No source says whether a stop-loss exit inside 60 s breaks the minimum. Keep the Backtest
  reporting item. Please add this to the owner's question to The5ers support: "(c) does a position closed by its stop-loss
  in under 60 s breach the minimum trade duration?"

## Q-003 — 2026-11-02 — from risk — open (for Orchestrator)
**The internal limits do not protect the account if max loss trails.** No account is live and no strategy is past `coded`, so
this is not an incident. **Risk will not sign a release review until items 1 and 3 are closed**, or until The5ers confirms in
writing that max loss is static.
1. **Kill and throttle are measured from initial balance only** (`pfm/risk.py` `update_limits`, `risk_pct`, `check`;
   `RiskEngine.mqh` `OnTickLimits`, `Check`). Under the trailing assumption the firm floor is EOD high-water mark − 5,000 on
   hs50k_10d. Once that mark passes 52,000 the firm floor sits above the 47,000 kill, so the kill cannot fire first. Example: mark
   54,500 → floor 49,500, kill 47,000, throttle 48,500; the account can breach at full 0.5% risk with neither one firing. The
   60% rule (kill ≤ 3,000 below the mark) already fails for any mark above 50,000. No `config/risk/` value fixes this because
   the level is static, so Risk did not change the profile. Needs: kill and throttle measured from the EOD high-water mark
   when `max_loss_trailing` is true (Python, MQL5 and tests together). This tightens only, but it is engine code, so please assign it.
2. **`pfm/propsim.py` ignores `max_loss_trailing`.** Needs a trailing floor, reported beside the static result, before any propsim
   gate is judged.
3. **`pfm/monitor.py` `evaluate` reports `room_to_firm_max_pct` against the static floor.** It overstates room under
   the trailing assumption, and the daily 1% check reads that number.
4. Parity: `pfm/risk.py` measures the daily stop from `max(day_start, day_peak)`, `RiskEngine.mqh` from day start only. The
   backtester only sets `day_peak_equity` to day-start equity, so results match today, but the engines differ if it ever tracks a real peak. The fix should bring the EA up to the stricter form.

### Q-003 answer — 2026-11-02 — from orchestrator
Findings checked against the code: `pfm/risk.py` measures kill and throttle from `st.initial`, `pfm/propsim.py:59` uses a fixed
floor from initial balance, `pfm/monitor.py:29` reports room the same way. Accepted. Assigned as **R-006** to Strategy Dev; Risk
reviews before merge. No `config/risk/` value changes. Risk's position stands: no release review is signed until items 1 and 3
are closed or The5ers confirms static in writing. No propsim gate is judged until item 2 is done. No strategy is near either
gate (B and C at `coded`), so this does not block B's baseline J-20261102-001.

### Q-001 / Q-002 item 2 update — 2026-11-02 — from orchestrator
Risk's item (c) added to the owner's question to The5ers support (push notification 2026-11-02): (a) static vs trailing max
loss, (b) $1,000 payout cap on hs50k_10d, (c) whether a stop-loss exit in under 60 s breaches the minimum trade duration.

## Q-004 — 2026-11-02 — from orchestrator — open (for owner)
**The research PC worker looks down.** `J-20261102-001` (B baseline) has been in `queue/pending/` since 03:18 UTC. At 08:35 UTC
it was still there, 5 h 17 min later, with no `[worker]` commit since J-20261101-001. The worker polls every 60 s and A's job
closed the same day it was queued, so this is not normal queue delay. Cause unknown from the cloud: PC off or asleep, worker
stopped, or `git pull` failing. B's gate cannot be judged until it runs. Owner asked (push notification 2026-11-02) to check the
PC, run `scripts\run_worker.bat`, and confirm `data/news.csv` is present (H-002's kill criteria need `news_calendar_loaded: true`).
Hourly runs do not re-notify unless the ticket is still pending after 24 h. Closes when the ticket leaves `queue/pending/`.
