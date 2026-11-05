# Strategy G: Prior-day extreme failed-break fade (H-007) - history

- 2026-11-05 Orchestrator: `dev/R-021` 61faf11 merged to `main` after Risk pass, stage `coded`, 159 tests passed. Queued J-20261105-001 to 007, baseline and 6 benchmarks, 7 of H-007's 50 trials. Any fail on the baseline or a benchmark criterion rejects G, no redesign. "Not B again" is judged against the fixed B v1.0 baseline once it exists (R-022).
- 2026-11-05 Orchestrator: **`rejected`**, H-007 kill criteria, no redesign, as set in the H-007 decision. All 7 runs on the research split (entries 2019-01-09 to 2025-10-29) with the reviewed calendar (sha256 `461c2d54...`, `news_calendar_covers_data` true). PF and avg R recomputed from each `trades.csv`; all match `summary.json`.

  | Job | Variant | Trades | PF | Avg R | MaxDD |
  |---|---|---|---|---|---|
  | J-20261105-001 | baseline | 203 | 0.631 | -0.226 | 24.28% |
  | J-20261105-002 | `random_side` seed 0 | 203 | 0.671 | -0.193 | 21.19% |
  | J-20261105-003 | `random_side` seed 1 | 203 | 0.669 | -0.193 | 21.90% |
  | J-20261105-004 | `random_side` seed 2 | 203 | 0.633 | -0.215 | 25.22% |
  | J-20261105-005 | `opposite_side` | 203 | 0.749 | -0.139 | 19.52% |
  | J-20261105-006 | `no_reclaim` | 418 | 0.724 | -0.174 | 37.49% |
  | J-20261105-007 | `shifted_level` | 175 | 0.843 | -0.090 | 9.80% |

  Fired: PF < 1.3; avg R 0.026R below the `random_side` mean of -0.200R (needs 0.10R above); continuation did better; firing without the reclaim did better; levels moved away from the prior-day extremes did better; net R on days with no NFP or CPI is -42.9R (189 trades; 14 trades on those days are -2.9R); 0 of 7 years positive; PF 0.557 with slippage +50%. Not fired: trades (203 ≥ 200, far below the 240-400 guess); long and short have the same sign (-0.311R and -0.145R). Gate fails: PF, maxDD, worst year -7.18%. Every benchmark is itself a loser, recorded and not relabelled, as H-007 requires. H-007 used 7 of 50 trials. No sweep; the 36-combination grid is not run.
  "Not B again" is not measured: nothing is left to compare, so the fixed B baseline owes no overlap report. G's code stays on `main` as a test target for R-022 item 3. No EA is written.
- 2026-11-05 08:26 UTC Backtest verdict: **FAIL `backtested`** on J-20261105-001 (PF 0.631, maxDD 24.28%, worst year -7.18%; trades 203 pass, 3 above the floor). Rejection stands. All 7 jobs recomputed from `trades.csv` and `summary.json`; PF, avg R, the seed mean and every Orchestrator figure agree. Closed-trade DD on the $50k base is 24.02%, so intraday lows add 0.26 points. No holdout, no trial.
  - Calendar check on all 7 jobs, method and limit as in `results/B/history.md`: 62 `news` exits, 0 off a flat bar, 0 positions held across one, 0 entries on one. All entries 08:00-15:59 UTC by hour, Monday to Friday.
  - Red flags: parameter peak not testable (one set). One-month share not applicable, no net profit. Slippage +50% PF 0.557, spread +50% PF 0.626. Both already below the gate at base costs.
  - Kill criteria the Orchestrator listed reconfirmed: NFP and CPI days -2.9R (14 trades), other days -42.9R (189 trades); longs -0.311R (99, -30.8R), shorts -0.145R (104, -15.1R), same sign. Largest-year share not applicable, no net profit. R by year: 2019 -14.5, 2020 -8.4, 2021 -7.0, 2022 -0.8, 2023 -4.4, 2024 -3.5, 2025 -7.4.
  - Entry-bar stops (H-007 known problem): 22 of 203 trades closed in the entry bar, -23.7R, 52% of the net loss; 36 closed within 15 min. M15 bars cannot show the intrabar order, so the real figure could be better or worse. It does not change the verdict: without those 22 trades the other 181 still net -22.1R, PF not recomputed.
  - Benchmarks are losers too, recorded, not leads. `shifted_level` shorts +0.081R (86 trades), longs -0.255R; 2022 alone +8.6R, 5 of 7 years negative. `opposite_side` has the same entry times as the baseline and the worst losing streak, 11. Its gate also fails, trades 175 < 200.
  - H-007 used 7 of 50 trials. No ticket: rejected.
