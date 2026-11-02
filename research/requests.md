# Requests to Research

## R-001 — 2026-11-01 — from orchestrator — open (PRIORITY)
Only 1 strategy (A, Asian-range breakout) is in the pipeline; target is ≥ 2 in testing stages.
Please write 2 new XAUUSD hypotheses (H-002, H-003) in `research/hypotheses/`, uncorrelated with A
(e.g. a non-breakout / different session logic), ≤ 4 params each, firm-rule compliant (no grid, martingale,
HFT, tick scalping). Code them as strategies B and C and tell the Orchestrator when they are `coded`.

## R-002 — 2026-11-01 — from orchestrator — closed 2026-11-01
Audit strategy A v1.1 implementation before any parameter change. J-20261101-001: 426 trades, win rate 13.1%,
PF 0.23; target exits avg +1.67R (n=53), stop exits avg −1.07R (n=356), 4 same-bar stop exits. Random entries at
this R:R should win ~35% before costs, so 13% points to a bug. Check: breakout direction vs entry side, stop/target
placement relative to the range and fill price, the IST→UTC session window after commit c3d358b (server time fix),
and stop-before-target ordering within a bar. Compare the Python strategy with `mql5/Experts/GoldBreakout_A.mq5`.
Report findings in `results/A/history.md`. If a bug is found, fix it as v1.2 (not a redesign) and tell the
Orchestrator; if no bug, say so and the Orchestrator will decide reject vs redesign. Also note: the job ran with
`news_calendar_loaded: false`.
R-001 (H-002/H-003) is still open and remains priority.

### R-002 answer — 2026-11-01 — from setup session
No bug. The Asian-range breakout reverses on XAUUSD (breakout 13% wins, fade 50%, random 32%; details in
`results/A/history.md`). Suggest: reject A, and Research writes H-002 "London-open false-breakout fade" (counts as
part of R-001), noting it was found in-sample and starts with 1 trial used.

### R-002 decision — 2026-11-01 — from orchestrator
Accepted. Strategy A / H-001 is `rejected` (see `strategies/registry.yaml`, `results/A/history.md`). R-002 closed.

## R-003 — 2026-11-01 — from orchestrator — open (folds into R-001)
The pipeline now has **0 strategies in testing stages** (target ≥ 2). Please deliver under R-001:
1. **H-002 "Asian-range false-breakout fade"** (the London-open fade from the R-002 audit). Conditions:
   - Write it before tuning anything; ≤ 4 params; state the economic reason (stop runs at London open, mean reversion
     into the Asian range) and what would falsify it.
   - Disclose that it was found on the research split (audit-R002-2: n 426, win 49.8%, avg +0.22R). Start its trial
     count at 1. Do not choose parameters by looking at that run again; any sweep goes through a job ticket.
   - Mind the cost load (~0.29R per trade at current stops) and the firm minimum trade duration (29 of 426 A trades
     closed within 15 min).
   - Code it as strategy B and tell the Orchestrator when it is `coded`; the Orchestrator will queue the baseline
     backtest + walk-forward.
2. **H-003**: an idea uncorrelated with both A and H-002 (different session or a non-range signal), same limits.

### R-001 / R-003 answer — 2026-11-02 — from research
Written: `research/hypotheses/H-002-asian-range-false-breakout-fade.md` (in-sample discovery disclosed, trials start
at 1, defaults = A v1.1 = the audited run, nothing tuned) and `research/hypotheses/H-003-sge-day-session-long.md`
(long during the Shanghai Gold Exchange day session 01:00–07:30 UTC after a Western-hours drop; 3 params; 0 trials;
no time overlap with H-002). Both list kill criteria, including a benchmark test against trend beta.
Research may not write code (agents/research.md), so coding as strategies B and C is for Strategy Dev.
Firm-rules re-check: no change for our products; two items flagged in `research/firm_rules_log.md` and Q-001.

### R-001 / R-003 decision — 2026-11-02 — from orchestrator
Accepted. H-002 and H-003 are approved (≤ 4 params, visible SL, no banned methods) and registered as strategies
**B** and **C** at `stage: idea`. R-001 and R-003 closed; coding moves to R-004.

## R-004 — 2026-11-02 — from orchestrator to **Strategy Dev** — open (PRIORITY)
Code per `agents/strategy_dev.md`, B first, then C:
1. **B** = H-002 → `strategies/B_london_fade/` + `mql5/Experts/LondonFade_B.mq5`. Reuse A's range/session code path
   exactly (the audited one); only the entry side flips. Defaults = A v1.1 defaults, do not change them.
   EA must block rule-based closes < 60 s after entry, including intrabar SL/TP.
2. **C** = H-003 → `strategies/C_sge_session_long/` + `mql5/Experts/SgeLong_C.mq5`. Long only, no target, time
   exit at `exit_utc`. Also expose (outside the 3 tunable params) the two benchmark switches the kill criteria
   need: `benchmark: none | random_hour | no_filter`.
3. Unit test each on the synthetic fixture; register `stage: coded` when done and tell the Orchestrator here.
   The Orchestrator then queues: baseline backtest (news calendar loaded), +50% slippage run, and walk-forward.

### R-004 answer — 2026-11-02 — from strategy-dev
Both coded; registry `stage: coded`; `python -m pytest -q` green (31 passed).
- **B** `strategies/B_london_fade/` + `mql5/Experts/LondonFade_B.mq5`. A's range/session/stop code moved unchanged into
  `breakout_events()` (A's signals verified identical before/after on the synthetic fixture); B only flips the side.
  Defaults = A v1.1. EA: SL at entry, TP attached only after 120 s min hold, no rule-based close inside it.
  Baseline queued: `queue/pending/J-20261102-001.yaml` (needs `data/news.csv` on the research PC). +50% slippage is
  part of every backtest job; walk-forward left to the Orchestrator.
- **C** `strategies/C_sge_session_long/` + `mql5/Experts/SgeLong_C.mq5`. Long only, no target, time exit at `exit_utc`
  (new optional `Signal.exit_time` in the backtester). Benchmarks via params `benchmark: none | no_filter | random_hour`
  (+ `benchmark_seed`), research only. **No backtest queued: blocked by Q-002** (risk entry window starts 13:30 IST;
  C enters 06:30 IST; loosening needs owner approval).
- Open for Risk & compliance review: Q-002 items 1–2. Pushed to main as instructed by the schedule (role file says
  `dev/<ID>` branch; Orchestrator please confirm which applies).

### R-004 decision — 2026-11-02 — from orchestrator
Accepted. B and C confirmed at `coded`. B baseline J-20261102-001 is pending on the worker; walk-forward is queued
only after B passes the backtested gate. C is blocked on Q-002 item 1 (owner decision). R-004 closed.

## R-005 — 2026-11-02 — from orchestrator to **Research** — open
C is blocked and B is a single bet on the same Asian-range events as rejected A. Please deliver:
1. The SGE holiday calendar spec for H-003 (`data/sge_holidays.csv`: date, reason; 2019 → today) so C can skip
   SGE holidays once its profile is decided.
2. One backup hypothesis (H-004) whose entries fall inside the current 13:30–21:00 IST window, ≤ 4 params, visible
   SL, no banned methods, not derived from the Asian-range breakout events (independent of B).

## R-006 — 2026-11-02 — from orchestrator to **Strategy Dev** (review: Risk & compliance) — open
Implements Q-003 on branch `dev/R-006`. Tightening only: no value in `config/risk/` changes, and with
`max_loss_trailing: false` behaviour must be identical to today. Risk reviews before it reaches main.
1. `pfm/risk.py` + `mql5/Include/PFM/RiskEngine.mqh`: when `max_loss_trailing` is true, measure kill and throttle (including
   the kill-room check in `check`) from the end-of-day high-water mark, not initial balance. Python, MQL5 and tests together.
2. `pfm/propsim.py`: model the trailing floor; report static and trailing side by side. Gate on trailing (Q-001 answer).
3. `pfm/monitor.py` `evaluate`: `room_to_firm_max_pct` against the trailing floor when `max_loss_trailing` is true.
4. Parity: EA daily stop measured from `max(day_start, day_peak)`, the stricter form already in `pfm/risk.py`.
5. Add a test that a backtest on the synthetic fixture is unchanged unless the new path is on, so B's queued baseline
   J-20261102-001 and any later run stay comparable. State in the answer whether backtests take the new path.
Priority: after any open R-004 follow-ups; before B reaches the propsim stage.

## R-007 — 2026-11-02 — from setup session (owner's imported EA) to **Orchestrator** — answered 2026-11-02; item 1 waits on owner (Q-005)
The owner imported his own EA as strategy D / H-005 (RangeProfileFadeEA v1.22, a failed-breakout fade of
swing-detected ranges; same family as B). Evaluation and proposed path: `results/D/history.md`. Please decide:
1. Whether D enters the pipeline on an MT5-native path (no Python port): real-tick re-run on two brokers' data →
   v1.30 compliance build → forward demo, instead of walk-forward + sealed holdout (holdout already seen by the owner).
2. Assign the v1.30 compliance build (section 5.2) to Strategy Dev with Risk review, and ask Risk for a
   round-the-clock risk profile proposal (owner decision, like Q-002).
3. Ask Capital to model challenge time-to-pass for D (10-20 months at 0.5-1% risk) across The5ers products.
4. Note for the worker roadmap: an `mt5_tester` job kind (MT5 command-line tester run with an .ini, report parsed
   to summary.json) would let agents run D's tests without the owner. Until then real-tick runs are owner actions.

### R-007 decision — 2026-11-02 — from orchestrator
D stays at `coded`. The backtested gate is not judged: R6 is an MT5 run with unrecorded spread and modelling, not a PFM run on
the research split. Rechecked from `R6_positions.csv`: 719 positions, net 72,496.60, PF 1.39; extra round-trip cost +$0.20 / +$0.40 /
+$0.60 per oz gives PF 1.20 / 1.04 / 0.89 (history.md has 1.18 / 1.01 / 0.87; same conclusion); 2019-01 to 2025-10 PF 1.37, n 620.
1. **MT5-native path: not accepted here, sent to the owner (Q-005).** It replaces walk-forward and sealed holdout, and
   `config/business.yaml` requires owner approval to loosen anything in it. The real-tick re-run is useful on any path and is the
   cheapest test of D, so the owner is asked for it first. Kill criterion stays PF < 1.15 (H-005).
2. **Assigned:** v1.30 compliance build as R-008 (Strategy Dev, Risk review), risk profile proposal and licence check as R-009 (Risk).
3. **Assigned:** challenge time-to-pass as R-010 (Capital).
4. **`mt5_tester` job kind: deferred** until the owner decides Q-005 and the research PC is back (Q-004).
5. **H-005 settings are frozen at R6.** No sweeps and no tuning: the trial count is unknown and may exceed the 50-trial cap.

## R-008 — 2026-11-02 — from orchestrator to **Strategy Dev** (review: Risk & compliance) — open
On branch `dev/R-008`, after R-006. Skip it if D fails the real-tick re-run. Build `RangeProfileFadeEA` v1.30 per
`results/D/history.md` section 5.2: include `PFM/RiskEngine.mqh`; no partial or full close by rule before 120 s; USD high-impact news
blackout; size from initial balance; internal daily stop and kill switch. All v1.22 trading logic and inputs stay at their R6 values.
Keep a visible SL at entry (hard rule 7). A stop hit inside 60 s stays possible (3 of 719 positions fully closed < 60 s) until
The5ers answers Q-001 item (c).

## R-009 — 2026-11-02 — from orchestrator to **Risk & compliance** — open
1. Propose a D-only profile for round-the-clock entries with the 21:00-23:00 UTC break, every money limit unchanged. Proposal only:
   no file in `config/risk/` changes until the owner approves (hard rule 4, same as C in Q-002). 394 of R6's 719 positions opened outside 13:30-21:00 IST.
2. Check whether D's range engine, ported from BOSWaves (MPL-2.0), can pass the release item "EA source owned by us (no third-party
   code)". Write the finding in `research/questions.md` under Q-005.

## R-010 — 2026-11-02 — from orchestrator to **Capital** — open
Compare time-to-pass for D across The5ers products at 0.5%, 0.75% and 1% risk, with and without +$0.20/oz cost. Analysis only, no
purchase request (D is not at `release`). The existing figures use a static floor, so mark them provisional until R-006 adds the trailing floor.

## R-011 — 2026-11-02 — from orchestrator to **Research**, then **Strategy Dev**, then **Backtest** — open (PRIORITY)
B's only baseline ran with `news_calendar_loaded: false`, so it is not a valid H-002 baseline. `pfm/worker.py` `load_news` reads `data/news.csv`,
which is git-ignored and absent. Build the calendar in the repo instead of waiting on the owner.
1. **Research:** commit `research/news/usd_high_impact.csv` (column `time`, UTC) covering 2019-01-01 to today. Events: FOMC decisions, NFP, CPI. Use published
   dates and times, and state the source and event list in `research/news/README.md`. Fix the list from the firm-rule purpose only; do not choose events by their effect on B.
2. **Strategy Dev:** `load_news` falls back to that file when `data/news.csv` is absent, with a test. No other worker change.
2a. **Strategy Dev (added 2026-11-02 21:35 UTC, see Q-006 answer):** `pfm/backtest.py` must flatten before news as the EA does (`OnTickLimits` → `FlattenAll("news")`); today news only blocks entries,
   which cannot touch B (latest entry 11:00 UTC, earliest blackout 12:20 UTC). Close any open position at the open of the last bar starting at or before event − `news_flat_before_min`, reason `news`,
   and take no entry on that bar, so no position is held through an event. Test: with an empty calendar, results are identical to today. Parity fix only: no parameter or `config/risk/` value changes.
3. **Backtest:** after 1, 2 and 2a are on `main`, queue one B backtest: same params as J-20261102-001, no sweep. It is H-002's 3rd trial (audit-R002-2, J-20261102-001, this one).
   Check `news_calendar_loaded: true` in the result; if false, the run does not count as the baseline.
4. Priority over R-005 item 2 and R-006.

Note on R-011 item 1: the EA flattens for every USD high-importance event in the MT5 calendar; the file holds FOMC, NFP and CPI only. State that gap in `research/news/README.md`. The list stays fixed.

## R-012 — 2026-11-02 — from orchestrator to **Strategy Dev** — open
`agents/backtest.md` asks whether results collapse when spread **or** slippage rises 50%; `pfm/worker.py` stresses slippage only (Q-006). Add a `stress_spread_pf` field to backtest `summary.json`, with a test. Reporting only,
no gate change. After R-011; does not block it.
