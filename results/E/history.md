# Strategy E history (H-004, US-open impulse continuation)

- 2026-11-03 Orchestrator: `coded`. Merged from `dev/R-013` (3a0901f) after Risk pass; 57 tests pass. Queued J-20261103-001 to 004 (baseline, `random_side`, `opposite_side`, `no_filter`), 4 of 50 trials. No results yet.
- 2026-11-04 Orchestrator: **`rejected`**, H-004 kill criteria. All 4 runs used the reviewed calendar (sha256 `461c2d54...`, `news_calendar_covers_data` true); exits checked against the calendar, see `results/B/history.md`.

  | Job | Variant | Trades | PF | Avg R | MaxDD |
  |---|---|---|---|---|---|
  | J-20261103-001 | baseline | 617 | 0.792 | -0.095 | 32.53% |
  | J-20261103-002 | `random_side` seed 0 | 617 | 0.707 | -0.145 | 44.56% |
  | J-20261103-003 | `opposite_side` | 617 | 0.719 | -0.137 | 43.89% |
  | J-20261103-004 | `no_filter` | 1703 | 0.784 | -0.097 | 91.16% |

  Fired: PF < 1.3; avg R only 0.050R above random (needs 0.10R); 2019-2023 net -41.6R; 0 of 7 years positive; PF 0.708 with slippage +50%. `no_filter` is about level with the baseline, so the large-impulse filter added 0.002R. Long and short are both negative. H-004 used 4 of 50 trials. No sweep: a kill criterion ended the hypothesis at defaults. Gate fails: PF, maxDD, worst year -7.67%.
