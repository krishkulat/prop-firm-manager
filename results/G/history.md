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
