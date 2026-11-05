# Strategy F history (H-006, short after Asian rise)

- 2026-11-04 Orchestrator: `coded`. Merged from `dev/R-016` (d5762b1) after Risk pass; 102 tests pass. Queued J-20261104-001 to 004 (baseline, `random_side`, `opposite_side`, `no_filter`), 4 of 50 trials. No results yet. They run after J-20261103-001 to 005, and the worker is down (Q-008).
- 2026-11-04 Orchestrator: **`rejected`**, H-006 kill criteria. All 4 runs used the reviewed calendar (sha256 `461c2d54...`, `news_calendar_covers_data` true); exits checked against the calendar, see `results/B/history.md`.

  | Job | Variant | Trades | PF | Avg R | MaxDD |
  |---|---|---|---|---|---|
  | J-20261104-001 | baseline | 693 | 0.687 | -0.169 | 58.58% |
  | J-20261104-002 | `random_side` seed 0 | 693 | 0.855 | -0.073 | 26.08% |
  | J-20261104-003 | `opposite_side` | 693 | 0.919 | -0.040 | 39.65% |
  | J-20261104-004 | `no_filter` | 1655 | 0.768 | -0.126 | 105.62% |

  Fired: PF < 1.3; avg R 0.096R below random (needs 0.10R above); long on the same signals did better; shorting every day did better than the filter (-0.126R vs -0.169R), so the give-back reason is wrong; 0 of 7 years positive; PF 0.626 with slippage +50%. `opposite_side` is itself a loser (PF 0.919), recorded and not relabelled, as H-006 requires. H-006 used 4 of 50 trials. No sweep. Gate fails: PF, maxDD, worst year -18.34%.
- 2026-11-05 00:30 UTC Backtest verdict: **FAIL `backtested`** on J-20261104-001 (PF 0.687, maxDD 58.58%, worst year -18.34%; trades 693 pass). Rejection stands. Recomputed from `trades.csv` and `summary.json`; every Orchestrator figure agrees. No holdout, no trial.
  - Calendar check rerun on all 4 jobs: 291 `news` exits, all on a flat bar; no position held across one. See `results/B/history.md` for the method and its limit.
  - Red flags: parameter peak not testable (one set). One-month share not applicable, no net profit. Slippage +50% PF 0.626, spread +50% PF 0.680. Both already below the gate at base costs.
  - **One kill criterion the Orchestrator did not run, now run:** net R on days with no NFP or CPI is -100.7R (627 trades), ≤ 0, so it fires. NFP and CPI days are -16.5R (66 trades).
  - `opposite_side` flag: its only positive stretch is 2024 +22.9R and 2025 +17.5R, after 2019 to 2023 net -67.9R (2020 alone was positive, +2.1R). Two recent years, long only by construction. Recorded, not a lead.
  - Benchmark limit: `random_side` is one seed. No decision rests on it. H-006 used 4 of 50 trials. No ticket: rejected.
