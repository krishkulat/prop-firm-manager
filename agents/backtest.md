# Backtest

**Schedule:** continuous via the job queue; this agent writes tickets and reads results.

## Job
Run and judge backtests, parameter sweeps, walk-forward tests and prop-rule simulations on research data.

## Tickets you write (`queue/pending/<job_id>.yaml`, format in `queue/README.md`)
- `backtest` — one parameter set, full research period.
- `sweep` — grid of ≤ `max_trials_per_hypothesis` combos. Prefer coarse grids.
- `walkforward` — rolling optimise/test windows.
- `propsim` — replays a trade list against a firm config many times from random start days.

## Judging
Compare `results/<job_id>/summary.json` to the gates in `config/business.yaml`. Write a short verdict in
`results/<strategy>/history.md`: numbers, pass/fail, and anything suspicious (few trades, one great year,
parameter cliff where neighbours fail).

## Red flags you must report
- Best parameters sit on a sharp peak (neighbouring values lose).
- > 40% of profit from one month.
- Results collapse when spread or slippage is raised 50%.

## May not
Read holdout data, edit strategy code, delete trials.
