# Strategy B: Asian-range false-breakout fade — history

## 2026-11-05 04:40 UTC — Orchestrator: every B figure below is contaminated (Q-010)
`breakout_events` let the 23:45 IST bar into the range, so signals were selected on the future. J-20261102-001, J-20261103-005 and audit-R002-2 stay counted (3 of 50 trials for H-002) but are not evidence, including the 7.70% maxDD behind the v1.1 redesign. Stage stays `coded`, `redesigns` stays 1, not refunded.
**Next, after R-022:** one v1.0 baseline on fixed code, H-002's 4th trial. Any H-002 kill criterion → rejected, v1.1 not run. Whole gate passes → v1.1 dropped, walk-forward. Only maxDD or worst year fails, no kill → v1.1 as trial 5, and any gate failure on it rejects B. R-019 on hold until then. See `research/questions.md`.

## 2026-11-05 00:30 UTC — Backtest verdict on J-20261103-005: FAIL `backtested` (maxDD), Orchestrator figures confirmed

Recomputed from `results/J-20261103-005/trades.csv` and `summary.json`. No market data read, no holdout, no trial. All Orchestrator figures above agree.

| metric | result | gate | |
|---|---|---|---|
| trades | 426 | ≥ 200 | pass |
| PF | 1.407 | ≥ 1.3 | pass |
| maxDD (0.5% risk, % of initial) | 7.70% | ≤ 6.0% | **FAIL** |
| worst year | -3.75% (2019) | ≥ -5.0% | pass |

Valid baseline: calendar loaded and covers the data. R-011 check rerun separately on all 9 jobs with `news_flat_bars` on an unbroken M15 grid: 312 `news` exits, 0 off a flat bar, 0 positions held across one, 0 entries on one. Same limit as the Orchestrator's check: the bars are not in the cloud.

**Role-file red flags**
- Parameter peak: not testable, one parameter set.
- Profit from one month: not flagged. Best month 2023-02 is 8.9% of net (limit 40%).
- Slippage +50%: PF 1.259. Spread +50%: PF 1.353 (first run with the worker's `stress_spread_pf`). Neither is a collapse, and both clear H-002's 1.1 kill line. Slippage +50% is below 1.3.
- Both +50% together: PF about 1.19 to 1.20, arithmetic on `trades.csv`, not a worker figure. The same method gives 1.251 and 1.339 for the single stresses against the worker's 1.259 and 1.353, so it reads slightly low.

**Other flags**
- **Drawdown:** worst stretch is still 2023-08-18 to 2024-02-05, 29 trades, -14.93R (was -16.56R in J-20261102-001). Closed trades give 7.42%, intraday lows add 0.28 points. Longest losing streak 8.
- **Uneven edge:** avg R by year 2019 -0.119, 2020 +0.259, 2021 +0.257, 2022 +0.332, 2023 +0.189, 2024 +0.105, 2025 +0.435. Excluding 2025, avg R is +0.173.
- **Shorts are thin in the last stretch:** -1.9R in 2023, +0.1R in 2024, then +17.4R in 2025. Longs were positive in both of those years. 2019 lost on both sides (-3.2R shorts, -4.3R longs).
- **NFP and CPI days:** 27 trades, -1.2R; other days 399 trades, +88.6R. Not an H-002 criterion; recorded only, the profit does not rest on those days.
- **Entry-bar stops:** 9 of 426, -9.7R. 21 closed within 15 min, 60 within 60 min. M15 bars cannot show whether any closed in under 60 s, so the firm minimum hold is still unproven at this level.
- **Same signals as audit-R002-2:** not independent evidence for the edge, as the Orchestrator's warning says.

**Trials:** H-002 has used 3 of 50 (audit-R002-2 logged under H-001, J-20261102-001, this job). `trials.csv` shows 2 rows under H-002.

**Next:** no ticket. `dev/R-019` does not exist on the remote yet, and the Orchestrator queues B v1.1's one run after the merge. No sweep, walk-forward or propsim, because the gate has not passed.

## 2026-11-04 21:30 UTC — Orchestrator decision on J-20261103-005 (backtested gate: FAIL, maxDD only)

**Decision: one redesign, `redesigns: 1` of 3, stage stays `coded`, as B v1.1 (R-019). Any gate failure on v1.1 rejects B, with no second redesign.**

| metric | result | gate | |
|---|---|---|---|
| trades | 426 | ≥ 200 | pass |
| PF | 1.407 | ≥ 1.3 | pass |
| maxDD | 7.70% | ≤ 6.0% | **fail** |
| worst year | -3.75% (2019) | ≥ -5.0% | pass |

**Valid baseline.** `news_calendar_loaded` true, `news_calendar_covers_data` true, sha256 `461c2d54...` equals the committed file (CRLF normalised), 251 events.

**R-011 calendar check, run by the Orchestrator on all 9 jobs (J-20261103-001 to 005, J-20261104-001 to 004).** 0 of 312 `news` exits fall off a flat bar, 0 positions are held across one, 0 entries land on one. Limit: flat bars were rebuilt from the calendar assuming an unbroken M15 grid, because the bars are not in the cloud; a missing bar would show as a mismatch and none did.

**H-002 kill criteria, none fired:** PF 1.407; 426 trades; PF 1.259 with slippage +50% (limit 1.1); largest year 2025 is 26.4% of net R (limit 50%); 6 of 7 years positive (minimum 5); longs +48.7R, shorts +38.7R, same sign. Net 87.4R, avg +0.205R. Walk-forward and holdout criteria are not reached.

**Why a redesign, not rejection.** Only maxDD failed and no kill criterion fired, so the failure does not disprove H-002. The news flatten cut maxDD from 8.52% to 7.70%, short of the 6.0% limit, so the same design will not pass.

**Why the midpoint target.** H-002 named it on 2026-11-02, before any baseline: "a range-midpoint exit is a possible later redesign". It is also the exit the liquidity-sweep reason predicts, since price is said to return into the range. It was not chosen from the 2023-08 to 2024-02 stretch, and that stretch was not examined for this decision. Risk stays at 0.5%: lowering it to pass is not allowed.

**Evidence warning.** B's edge has still only been seen on the split that produced it (audit-R002-2). A v1.1 pass is evidence for walk-forward to test, not a confirmed edge.

**Set before v1.1 runs:**
- One backtest at stop_atr 1.2, min_range_atr 1.5, max_range_atr 4.0, no sweep. H-002's 4th trial of 50.
- Passes all four limits and no H-002 kill criterion fires → queue walk-forward.
- Fails any limit, or a kill criterion fires → `rejected`.

## 2026-11-03 — Backtest: clean baseline queued (R-011 item 3)

No B job finished since J-20261102-001, so no new verdict. R-011 items 1, 2 and 2a are on `main` (orchestrator merge 07:35 UTC). Queued `queue/pending/J-20261103-005.yaml`: same params, data and risk profile as J-20261102-001, no sweep.
H-002's 3rd trial of 50 (audit-R002-2, J-20261102-001, this one). The rules set in the 2026-11-02 Orchestrator decision below apply to the result.
Parsed and run once on the synthetic fixture through `run_one`, not `run_job`, so no trial was logged: 251 news rows load, stage `coded`.

**Check on the result:** `news_calendar_loaded: true` is required, and it does not say which file was read. `load_news` prefers `data/news.csv`, which Q-004 asked the owner to put on the research PC. If that file exists, this run does not use the reviewed R-011 calendar.

## 2026-11-02 21:35 UTC — Orchestrator: Q-006 closed, R-011 amended

Stage unchanged: `coded`, `redesigns: 0`. Gate-basis closed-trade DD is 8.24% of initial (6.04% was % of peak).
News blocks entries only in `pfm/backtest.py`, and B's entries end at 11:00 UTC, before any FOMC/NFP/CPI blackout, so R-011 as written would repeat J-20261102-001 and waste a trial.
The EA flattens before news; the backtest did not. R-011 item 2a adds that. **Do not queue the baseline until 1, 2 and 2a are on `main`.** The rules set below stand. If maxDD still fails, the choice between
one redesign and rejection is made then, and a redesign must not be picked by looking at the 2023-08 to 2024-02 stretch.

## 2026-11-02 — Orchestrator decision on J-20261102-001 (backtested gate: FAIL)

**Decision: held at `coded`, `redesigns: 0`. Not rejected.** Evidence: `results/J-20261102-001/summary.json`, full table in
`results/reports/daily/2026-11-02.md`.

- Gate: trades 426 (pass), PF 1.427 (pass), maxDD 8.52% vs 6.0% (**fail**), worst year -2.99% (pass). Trades run 2019-01-14 to 2025-10-29; none in the holdout window.
- **Invalid as a baseline:** `news_calendar_loaded: false`. The ticket and H-002's kill criteria require it loaded.
- **No H-002 kill criterion fired** on this run (PF, trades, +50% slippage PF 1.282, year concentration, long/short sign).
- **Same numbers as audit-R002-2**, the run that produced the idea, so this adds no new evidence for the edge.

**Next:** one clean baseline at the same parameters (R-011). No walk-forward until the gate passes.

**Set before that run:**
- Passes all four limits → queue walk-forward.
- Fails only maxDD → Orchestrator chooses one redesign (counts toward the 3) or rejection. Closed-trade DD on the gate's basis is 8.24% (corrected from 6.04%, see Q-006).
- PF < 1.3 or trades < 200 → H-002 kill criterion: rejected.
- Lowering risk below 0.5% to pass is not allowed: the gate is defined at 0.5% risk.

## 2026-11-02 — Backtest verdict on J-20261102-001: FAIL `backtested`, not a valid baseline

B v1.0, rr 2.0 / stop_atr 1.2 / range 1.5-4.0x, research split, M15, research mode (no kill switch). Agrees with the Orchestrator's decision above.

| metric | result | gate | |
|---|---|---|---|
| trades | 426 | ≥ 200 | pass |
| PF | 1.427 | ≥ 1.3 | pass |
| maxDD (0.5% risk, % of initial) | 8.52% | ≤ 6.0% | **FAIL** |
| worst year | -2.99% (2019) | ≥ -5.0% | pass |
| `news_calendar_loaded` | false | required by H-002 | **invalid baseline** |

Yearly %: 2019 -2.99, 2020 +8.67, 2021 +8.27, 2022 +11.71, 2023 +5.87, 2024 +2.31, 2025 +12.33. Win rate 49.8%, avg +0.221R, Sharpe 1.18.
Exits: 201 stop, 165 target, 60 session end. Last exit 2025-10-29.

**Role-file red flags**
- Parameter peak: not testable, one parameter set.
- Profit from one month: not flagged. Best month 2025-09 is 9.6% of net (limit 40%).
- Slippage +50%: PF 1.282. Not a collapse and above H-002's 1.1 kill line, but below 1.3.
- Spread +50%: **not tested by the worker**, it stresses slippage only. Estimate from the trade list, charging +$0.125/oz per trade (assumes 25-pt spread): PF ≈ 1.36; with slippage +50% as well, PF ≈ 1.22. The same method gives 1.273 for slippage alone against the worker's 1.282, so treat these as approximate. Arithmetic on `trades.csv`, no market data read, no trial.

**H-002 kill criteria on this run (none fired; run is not the valid baseline)**
- Largest year 2025 = 26.9% of net R (limit 50%). 6 of 7 years positive (minimum 5).
- Longs +54.2R (n 190, avg +0.285), shorts +40.0R (n 236, avg +0.170): same sign.

**Other flags**
- **Drawdown is a long losing stretch, not one bad day.** 2023-08-18 to 2024-02-05: 29 trades, -16.56R. Longest losing streak 8. On the gate's basis (% of initial) closed trades alone give **8.24%**, so intraday lows add only 0.28 points.
- **Correction to the 6.04% closed-trade figure** in `results/reports/daily/2026-11-02.md` and the section above: that is the same stretch as % of peak equity, not % of initial. Reaching 6.0% needs the news filter to remove about 2.5 points, roughly 5R, of that stretch. See Q-006.
- **Weak recent edge before 2025:** 2024 made +4.8R, and shorts lost -2.2R in 2023. 2025 alone is +25.3R.
- **Entry-bar stops (Q-002 item 2 reporting):** 9 of 426 trades hit the SL in the entry bar, all stops, -9.7R total. 21 closed within 15 min and 60 within 60 min. M15 bars cannot show whether any closed in under 60 s.
- Same numbers as audit-R002-2, so this is not independent evidence for the edge. `yearly_pct` lists an empty 2018, as in A's run.

**Trials:** H-002 has used 2 of 50 (audit-R002-2, logged under H-001, and this job). `trials.csv` shows 1 row under H-002.

**Next:** no ticket queued. R-011 steps 1 and 2 are not on `main` (`research/news/` is absent, `load_news` still reads only `data/news.csv`), so a run now would repeat this job and spend a trial for nothing. Queue the clean baseline once both land. No sweep, walk-forward or propsim until the gate passes.

- 2026-11-10 — [orchestrator] **Stage → `rejected`.** J-20261109-002 (B v1.0.1 = v1.0 on fixed code 5f43fae, defaults, news calendar loaded and covering the data, H-002 trial 4) hit the H-002 kill criterion "baseline PF < 1.3": PF 0.679, 989 trades, win 33.0%, avg −0.223R, maxDD 114.51%, worst year −21.15%, 0 of 7 years positive, stress-slip PF 0.605. Per the Q-010 plan, v1.1 (R-019) is not run and redesigns stays 1. A and B (exact mirrors) both lose about 0.2R a trade: on clean code neither side of the Asian-range break has an edge after costs. The earlier +0.22R fade figure came from the look-ahead.
