
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
