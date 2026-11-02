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
