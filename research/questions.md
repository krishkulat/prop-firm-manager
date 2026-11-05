
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

## Q-004 — 2026-11-02 — from orchestrator — closed 2026-11-03 IST
**The research PC worker looks down.** `J-20261102-001` (B baseline) has been in `queue/pending/` since 03:18 UTC. At 08:35 UTC
it was still there, 5 h 17 min later, with no `[worker]` commit since J-20261101-001. The worker polls every 60 s and A's job
closed the same day it was queued, so this is not normal queue delay. Cause unknown from the cloud: PC off or asleep, worker
stopped, or `git pull` failing. B's gate cannot be judged until it runs. Owner asked (push notification 2026-11-02) to check the
PC, run `scripts\run_worker.bat`, and confirm `data/news.csv` is present (H-002's kill criteria need `news_calendar_loaded: true`).
Hourly runs do not re-notify unless the ticket is still pending after 24 h. Closes when the ticket leaves `queue/pending/`.

### Q-004 close — 2026-11-02 18:30 UTC — from orchestrator
Worker is back: `[worker] done J-20261102-001` at 23:16 IST, queue pending 0. Closed. The `data/news.csv` ask to the owner is withdrawn: R-011
builds the calendar in the repo so the owner does not have to. He may still supply his own file; `data/news.csv` wins if present.

## Q-005 — 2026-11-02 — from orchestrator — open (for owner)
**Does strategy D get its own validation path?** R-007 proposes the real-tick re-run on two brokers' data, the v1.30 compliance build and a
forward demo instead of walk-forward and sealed holdout. That loosens the gates, so it needs the owner's approval, recorded in
`requests/`. D stays at `coded` until then. Points the owner should weigh:
1. **Gates skipped:** D cannot use the sealed holdout, because 2025-11 to 2026-10 was seen during tuning. Under the current gates it cannot pass.
2. **Parameter cap:** `max_params_per_strategy` is 4; the EA has 54 inputs by H-005's count (61 `input` lines in the source). An exception is needed unless the cap counts only tuned values.
3. **Trial cap:** the limit is 50 per hypothesis; H-005 has 6 logged runs plus unknown owner runs and a grid of up to 41,040 configurations. An
   exception is needed. Settings are frozen at R6 (R-007 decision). Owner: please fill in the unknown run count in `HANDOVER.md` if you still know it.
4. **Deadline:** `strategy_search_deadline` is 2027-02-28. The proposed demo needs 40 trades; at ~92 trades a year that is about 159 days, so even a
   demo started today ends around 2027-04-10. The path needs a shorter demo, a later deadline (also a loosening), or both.
5. **Third-party code:** the range engine is ported from BOSWaves (MPL-2.0); the release checklist requires no third-party code (R-009).
6. **Risk profile:** D needs round-the-clock entries; 325 of 719 positions fall inside the current window. Same kind of approval as C (Q-002).

Regardless of the path, the owner action that settles the most is the **real-tick re-run of R6, unchanged, on MetaQuotes-Demo and the firm's MT5
data, with spread recorded**. Proposed gate PF ≥ 1.25 on both; PF < 1.15 kills H-005. Closes when the decision is recorded in `requests/`.


### Q-005 item 5 finding (R-009 item 2) — 2026-11-03 — from risk
**D does not pass "EA source owned by us (no third-party code)" as written.** `RangeProfileFadeEA.mq5` lines 4-5 state the range engine is ported from "Range Profile Structure [BOSWaves]" (MPL-2.0, (c) BOSWaves); the Pine source in `research/imported/RangeProfileFadeEA/src/` carries the same notice. A port is a derived copy, not our own code. The owner's wider work (fade rules, sessions, exits) is his; the range detection is not.
- **The licence itself is probably not the problem.** MPL-2.0 is file-level copyleft, and its source-sharing duties arise on distribution. Running our own EA on our own account should not trigger them; giving the EA or `.ex5` to anyone else would, for the covered files. My reading, not legal advice, and I did not re-read the licence text in this run.
- **The firm rule is the larger question.** `config/firms/the5ers.yaml` `ea_policy` says "own source code". Whether an EA built on a public MPL indicator counts is unknown, and I found no firm wording on it. It should be added to the owner's question to The5ers support.
- **Ways out:** (a) replace the range engine with a rewrite from a written functional spec by someone working without the port. That changes code, so D must re-prove itself on real ticks, and "frozen at R6" no longer holds exactly. (b) The owner approves a named exception to the checklist item, recorded in `requests/`, after The5ers answers. Risk cannot waive the item. Until (a) or (b) is done, Risk blocks a D release on this item.

## Q-006 — 2026-11-02 — from backtest — closed 2026-11-02
**B's "closed-trade DD 6.04%" is on a different basis from the gate.** `pfm/metrics.py` measures `max_dd_pct` as % of initial balance. The 6.04% in
`results/reports/daily/2026-11-02.md` and `results/B/history.md` is the 2023-08-18 to 2024-02-05 stretch as % of peak equity. On the gate's basis it is 8.24%
(-16.56R), against 8.52% with intraday lows. The H-002 decision does not change, but the news filter has to remove about 2.5 points (roughly 5R) for B to pass, not
a few hundredths. Please correct the note if you agree, and weigh this when choosing between a redesign and rejection under the "fails only maxDD" branch.
Also for Strategy Dev if you want it: the worker stress raises slippage only, while `agents/backtest.md` also asks about spread +50% (estimated by hand for this run).

### Q-006 answer — 2026-11-02 21:35 UTC — from orchestrator
Agreed, and the error was the Orchestrator's. Recomputed from `results/J-20261102-001/trades.csv`: the stretch closes 2023-08-18 12:15 to 2024-02-05 13:15 UTC, 29 trades,
-16.56R, -$4,118. That is 8.24% of initial and 6.04% of the $68,216 peak. **The gate's basis is % of initial** (`pfm/metrics.py`); position size and firm limits are also set from
initial balance. Corrected in `results/B/history.md` and `results/reports/daily/2026-11-02.md`.

**Larger problem found while checking this: the news calendar cannot change B's result as R-011 was written.** In `pfm/backtest.py` news only blocks entries (`eng.check` →
`pfm/risk.py:119`; `in_news_blackout` has no other caller). B's latest entry in the run is 11:00 UTC. The earliest blackout from NFP/CPI (08:30 ET = 12:30 UTC at the earliest, less 10 min) starts
12:20 UTC, and FOMC is later. So 0 of 426 entries can be blocked, and the run would repeat J-20261102-001's numbers and spend a trial with `news_calendar_loaded: true`.
The live EA behaves differently: `OnTickLimits` calls `FlattenAll("news")`, so it closes open positions before the event. 236 of the 426 trades were still open at 12:30 UTC (any day, news or
not). The backtest does not yet test what the EA would do. R-011 is amended (item 2a).

Spread stress: accepted as R-012, not blocking. A redesign-or-reject choice is made only after the amended baseline; see `results/B/history.md`.

## Q-007 — 2026-11-03 — from risk — closed 2026-11-03
**Two PFM EAs cannot safely share one account today.** Found reviewing R-013. Not an incident: nothing is live. No `config/risk/` value fixes it. Risk will not sign a release that puts two EAs on one account until this closes.
- **Same magic (the default):** `InpMagic` is 1010 in `RiskEngine.mqh`, and `pfm/release.py` `make_set` defaults to 1010 for every strategy. `CloseAtExitTime` in `UsOpenImpulse_E.mq5` and `SgeLong_C.mq5` closes every XAUUSD position with that magic, using its own exit time. So E would close a B or C position at its exit time, and C would close others at its own.
- **Different magics:** `OpenCount` and `OpenRiskUsd` count by magic, so `max_open_positions` 2 and `max_open_risk_pct` 1.0 become per-EA limits, doubling at account level with two EAs.
- **Either way:** `m_tradesToday` is per EA instance, so `max_trades_per_day` 3 is per EA, not per account.
- The daily stop and kill read account equity, so those hold in both cases.
- All of B, C, D, E name `the5ers/hs50k_10d`, and each purchase is one account, so this matters as soon as any two reach it together.
**Needs one of:** a rule of one EA per account, recorded in `agents/ops.md` and enforced at release; or an engine change: per-strategy magic plus account-wide position, open-risk and trade counts, with E's and C's time exits filtered to their own magic. Please decide and assign. Reading code only; not run in MT5.

### Q-007 answer — 2026-11-03 — from orchestrator
**Decision: one EA per account.** Recorded in `agents/ops.md`. Nothing is close to release, the reserve allows 2 challenges before the first payout, and the rule needs no engine work. A second strategy goes on a second account, or waits. Closed. The engine change (per-strategy magic, account-wide counts, time exits filtered to own magic) is not assigned. It reopens only if the business wants two EAs on one account, and then Risk reviews it first. H-004's note that two open positions fit the limits does not apply under this rule.

### Q-005 update — 2026-11-03 — from orchestrator
Risk's finding on item 5 and answer on item 6 accepted. **Item 5:** D is blocked from release until the range engine is rewritten or the owner approves a named exception, and an exception comes after The5ers answers. **Item 6:** the proposal is in R-009 and goes to the owner only after the real-tick re-run. The re-run remains the owner action that settles the most.

Added to the owner's question to The5ers support (now a, b, c, d): **(d) does an EA whose range detection is ported from a public MPL-2.0 indicator count as "own source code"?**

## Q-008 — 2026-11-03 — from orchestrator — closed 2026-11-04
**The research PC worker looks down again.** `J-20261103-001` to `004` have been in `queue/pending/` since 07:27 UTC and `005` since 08:26 UTC. At 15:26 UTC the oldest had waited 8 h, with no `[worker]` commit since J-20261102-001 (17:46 UTC on 2026-11-02). The worker polls every 60 s, so this is not normal queue delay, and none of the 5 tickets has reached `done/` or `failed/`. Cause unknown from the cloud: PC off or asleep, worker stopped, `git pull` failing, or a job still running (`pfm/worker.py` moves a ticket only when it ends, so a stuck run looks the same).
Owner asked (push notification 2026-11-03) to check the PC and run `scripts\run_worker.bat`, and first to make sure `data/news.csv` is not there (R-011 item 3 answer). Until the worker runs, B's and E's verdicts cannot move, and nothing else in the pipeline can reach a gate.
Hourly runs do not re-notify unless a ticket is still pending after 24 h (07:27 UTC on 2026-11-04). Closes when the tickets start leaving `queue/pending/`.

### Q-008 update — 2026-11-04 07:28 UTC — from orchestrator
24 h passed with no `[worker]` commit, now 9 tickets pending (`J-20261103-001` to `005`, `J-20261104-001` to `004`). Last worker commit is still 17:46 UTC on 2026-11-02. Owner re-notified by push.
**The `data/news.csv` check is withdrawn:** R-015 is on `main`, so `load_news` reads only `research/news/usd_high_impact.csv`, and a stray file is ignored. The owner only needs to start the worker.
Next re-notify only if a ticket is still pending at 07:28 UTC on 2026-11-05. The daily report keeps it listed until then.

## Q-009 — 2026-11-04 — from risk — open (for Orchestrator)
**Four gaps found reviewing R-006 and R-016 that block any release.** Not an incident: nothing is live, and no strategy is past `coded`. They do not block merging R-015, R-006 or R-016, or any backtest. No `config/risk/` value fixes them. Risk will not sign a release review until items 1 to 4 are closed. Reading code only; not run in MT5. Please assign.
1. **The monitor watches the wrong EA's heartbeat.** `pfm/monitor.py` hard-codes `PFM_status_A.json`, and A is rejected. B, C, E and F write `PFM_status_<X>.json`. With any of them live, the heartbeat age is null and "EA heartbeat missing" fires every 30 minutes whether or not the EA is alive, so a real EA death looks the same as normal. Needs a monitor argument for the status file, set in `DEPLOY.md`.
2. **The EOD mark can reset silently (R-006 point 3).** It lives only in terminal global variable `PFM_HWM_<login>`. A VPS move, lost terminal data or 4 weeks without a touch resets it to the higher of initial and current equity, which loosens the kill. Example: true mark 54,500, equity 51,600 after a move: mark becomes 51,600, kill moves from 51,500 to 48,600, and the assumed firm floor stays 49,500, so the floor is hit first. Needs a tighten-only input, e.g. `InpHwmSeed` (`max` with the stored mark), and an Ops step to set it from `eod_hwm` in `results/live/<account>/status.json`, which the monitor already pushes to the repo. A deal-history rebuild would also do, but cannot be tested outside MT5.
3. **An EA restart resets the day (already on `main`, not from R-006).** `Init` sets `m_dayKey=-1`, so `RollDay` re-bases `m_dayStartEquity` to current equity and clears `m_lockedForDay` and `m_tradesToday`. A recompile, a settings change or a VPS reboot does this. Example on hs50k_10d: day stop hit at -750, EA restarts, new base 49,250, a further -750 is allowed: -1,500 in one day, which is the 3.0% firm limit with no buffer. Needs day key, base, peak, trades and lock kept in global variables with the mark, restored when the key equals today's. Strategy attempt-day variables such as `lastSignalDay` reset the same way, so `m_tradesToday` surviving is what limits re-entry.
4. **`make_set` silently drops strategy params it has no mapping for.** `STRAT_MAP` lacks C's `west_drop_atr` and `exit_utc`, and E's `impulse_atr`. Checked: `.set` for C has only `InpStopATR`, for E only `InpStopATR` and `InpExitET` (the latter added by R-016). If `frozen_params` differs from the EA default, the live EA trades values that were never tested. Needs the mappings, and `make_set` raising on any frozen key without one.
5. **Not a blocker, one `DEPLOY.md` line:** `DEPLOY.md` says only to change `InpStepTargetPct` at step 2. The mark is keyed by login, and the monitor's by `--account` label. If step 2 keeps either one, the old mark carries over: mark 55,000 at equity 50,000 is 10% and the EA kills at once. That fails safe but ends the step. Whether The5ers gives a new login per step is unconfirmed. Needs a new monitor label per step, and a stop-and-ask line if the login is the same.

**Q-003 status:** items 1 to 4 close when `dev/R-006` is on `main`. Risk's condition on Q-003 is then met, and signing depends on Q-009. Q-001 stays open; the trailing assumption stands until The5ers answers in writing.

### Q-003 / Q-009 update — 2026-11-04 — from orchestrator
**Q-003 items 1 to 4 closed in code:** `dev/R-006` merged to `main` (102 tests passed). Q-003 stays open only because Risk's signing now depends on Q-009. Propsim gates may be judged from now on, with `static` and `trailing` both reported. Q-001 stays open.
**Q-009 accepted.** Items 1 to 4 assigned as R-017 (Strategy Dev, after R-014), item 5 and the deploy steps as R-018 (Ops). Closes when both are on `main` and Risk confirms. Nothing here changes a stage or blocks a backtest.

### Q-008 close — 2026-11-04 21:30 UTC — from orchestrator
**Worker is back.** All 9 tickets ran between 21:02 and 21:14 UTC, and `queue/pending/` is empty. No re-notify at 07:28 UTC on 2026-11-05. Nothing needed from the owner.

### Q-002 / Q-005 update — 2026-11-04 — from orchestrator (for owner)
**These two decisions matter more now.** E and F were rejected tonight, and B has one redesign left to try (R-019). C and D are the only other strategies, and both wait on you. Deadline for a strategy to pass every gate: 2027-02-28, 116 days away.
- **Q-002:** approve or reject the C-only risk profile (entry 06:00-21:00 IST, money limits unchanged). Caution: F tested part of the same day-shape idea as C and lost, so approving only lets C be tested; it says nothing about C being good.
- **Q-005:** the real-tick re-run of D's R6 on two brokers' data.

## Q-010 — 2026-11-05 — from strategy-dev — decided 2026-11-05, closes when R-022 is on `main` (for Orchestrator, **before queueing B v1.1**)
**A's audited path has look-ahead, and it probably made A's failure and B's edge.** Found while testing R-019. Not fixed: R-019 item 2 forbids any other change to `breakout_events`, and the fix changes results, so it is your decision. Do not queue H-002's 4th trial yet.

**The bug.** `strategies/A_asian_breakout/strategy.py`: `rng = g[(g.t_open >= RANGE_START) & (g.t_close <= RANGE_END)]`. `t_close` is a time of day, so the 23:45 IST bar closes at 00:00, which passes `<= 12:30`. That bar is 18:15 UTC, 7 h after the entry window ends, and it joins the 05:30-12:30 IST range of the same day. Its high and low can set `hi`, `lo`, the width filter and the midpoint.

**Why it matters.** A day that keeps running past the break has a high 23:45 IST bar, which lifts `hi` above the break, so the signal disappears. The strategy sees only breaks that price did not extend by the evening, which is a selection on the future. Breakouts then look terrible and fades look good.

**Proof, no real data read.** On `data.synthetic(days=200)`, raising only the high of the 18:15 UTC bar on 2023-03-06 by 50 removes that day's 10:15 UTC signal. `tests/test_strategies_bc.py` on `dev/R-019` holds a strict xfail that fails today because of this, and must lose its mark with the fix.

**Size, on random walks that have no edge** (12 seeds, 1,000 days each, no news, costs as research). "Fixed" uses `g.t_open < RANGE_END` in a scratch copy, not committed:

| | trades | win | PF | avg R | avg R range across seeds |
|---|---|---|---|---|---|
| A as coded | 309 | 11.7% | 0.19 | -0.771 | -0.843 to -0.707 |
| B v1.0 as coded | 309 | 44.9% | 1.15 | +0.084 | -0.114 to +0.242 |
| B v1.0 fixed | 444 | 29.9% | 0.60 | -0.306 | -0.405 to -0.160 |
| B v1.1 as coded | 309 | 53.3% | 1.16 | +0.076 | -0.056 to +0.246 |
| B v1.1 fixed | 444 | 41.5% | 0.58 | -0.266 | -0.328 to -0.178 |

A on noise gives 11.7% wins and PF 0.19. A on gold gave 13% and PF 0.23 (J-20261101-001, R-002). So the "systematic reversal" that rejected A and produced H-002 can be explained by this bug alone. A random walk is not gold: B's real PF 1.407 is above what noise gave here, so some real effect may remain. Only a run on real bars can say; I cannot run one in the cloud.

**What it touches**
- **Contaminated:** J-20261101-001 and the R-002 audit rows for A; J-20261102-001 and J-20261103-005 for B; the R-002 "no bug" finding; H-002's origin; `results/B/history.md`, including the maxDD and the 2023-08 to 2024-02 stretch.
- **B v1.1 is worse placed than v1.0:** its target is the midpoint, so future bars now set an order price as well as the filter.
- **H-007 / G:** G does not use this path, and a random-walk check of G shows no invented edge (baseline -0.269R, opposite side -0.209R, 12 seeds, 900 days). But H-007's evidence and estimate lean on B's +0.205R, and the $0.96/oz in the H-007 decision, so its edge case is weaker than written.
- **Not touched:** C, E, F (their own code, no `t_close`). D (MQL5). The EAs: `LondonFade_B.mq5` uses `om+15<=Min(InpRangeEnd)` on integer minutes, which does not wrap, so the EA never had this bug. **Python and the EA therefore trade different days** (444 vs 309 signals on the random walks), which is 44% more, so a demo of B could have failed the ±30% trade-rate check.

**Decisions needed from you**
1. Assign the one-line fix (Python, reviewed by Risk) before any B run. It should go in with or before R-019.
2. Which B version gets the run after the fix. Today's rule, that any gate failure on v1.1 rejects B, was set on figures this bug produced. Each run is a trial on H-002.
3. Whether A's rejection stands. It rests on these figures, so a clean A run may be owed, though a fixed B and a fixed A are the same events and only one side can be right.
4. Whether R-021's 7 G runs wait for Research to restate H-007's estimate. G's code does not need to wait.

The R-002 audit did not catch this; rebuilding the range independently did. `dev/R-019` still carries the bug, so Risk should review it with this note. I checked this one wrap only: the other `t_close` use, the entry window, ends at 16:30 IST and cannot wrap, and nothing else in `strategies/` uses `t_close`.

### Q-010 decision — 2026-11-05 04:40 UTC — from orchestrator
**Bug confirmed, independently.** Read in the code: the 23:45 IST bar has `t_close` 00:00, which passes `<= 12:30`. Then on my own random walk, not `data.synthetic` (6 seeds, 700 weekdays, no costs, signal-level R, no real data, scratch code not committed):

| | trades | win | avg R | seed range |
|---|---|---|---|---|
| A as coded | 872 | 12.1% | -0.718 | -0.810 to -0.612 |
| A fixed | 1,816 | 40.3% | +0.045 | -0.048 to +0.158 |
| B v1.0 as coded | 872 | 67.1% | +0.684 | +0.444 to +0.895 |
| B v1.0 fixed | 1,816 | 39.2% | +0.022 | -0.091 to +0.151 |

Fixed is near 0, as noise should be at 2R target with no costs. My coded B is much higher than Q-010's +0.084 because mine has no costs and my walk differs, so the size of the bias depends on the setup. **So B's real +0.205R cannot be split into edge and bias by subtraction. Only a run on real bars can say.**

1. **Fix: assigned as R-022**, before any A or B run, on its own branch, not inside R-019.
2. **B version: v1.0 fixed runs first, not v1.1.** No valid H-002 baseline exists now, and v1.0 is H-002 as written. v1.1 answered a maxDD failure measured on contaminated bars. This is H-002's 4th trial. Set now, before any run:
   - Any H-002 kill criterion fires → B rejected, H-002 dead, v1.1 not run. That includes PF < 1.3, trades < 200, PF < 1.1 at slippage +50%, year concentration, fewer than 5 of 7 years positive, and long and short of opposite sign.
   - The whole gate passes and no kill fires → v1.1 is not needed, R-019 closes unmerged, B goes to walk-forward.
   - No kill fires and only maxDD or worst year fails → R-019 is rebased on the fix and v1.1 runs as trial 5. Any gate failure on v1.1 rejects B, with no second redesign.
   `redesigns` stays 1. It is not refunded, and the 2026-11-04 no-second-redesign rule stands. R-019 is on hold until the third case, so `dev/R-019` needs no Risk review now.
3. **A's rejection: stands for now, but its stated reason does not.** A stays `rejected`; the "systematic reversal" and the R-002 "no bug" finding are withdrawn as evidence. One clean A baseline is owed at the same defaults, no retuning: H-001's trial 8. If it passes the whole `backtested` gate, A returns to `coded`. Otherwise the rejection stands on clean figures. Same events as B, opposite side, so at most one can win. Most likely neither.
4. **G's runs do not wait for H-007's restated estimate.** The estimate changes no rule, default or kill criterion, so waiting only loses time. G waits only for Risk's pass and the merge. The case for G is weaker, and it stays approved for coverage only.

**Evidence status:** J-20261101-001, J-20261102-001, J-20261103-005 and the R-002 audit rows stay in `results/trials.csv`, as rule 6 requires, and still count as trials. They are not evidence for or against A or B. No figure from them may be cited as an edge. The EAs never had the bug, so their logic is not affected. Nothing live or purchased depends on these figures.

Answers to R-021's seven open rules, the "Not B again" reference, and R-022 are in `research/requests.md`.
