# Job queue

Agents drop tickets in `pending/`. The worker (`python -m pfm.worker`) on the research machine pulls the repo,
runs the oldest ticket, writes `results/<job_id>/`, appends to `results/trials.csv`, moves the ticket to
`done/` or `failed/`, commits and pushes.

## Ticket format (`queue/pending/<job_id>.yaml`)
```yaml
job_id: J-20261101-001        # unique; date + counter
kind: backtest                # backtest | sweep | walkforward | propsim | holdout
strategy: A                   # key in strategies/registry.yaml
hypothesis: H-001
requested_by: backtest        # role
data: {symbol: XAUUSD, timeframe: M15}
params: {rr: 2.0, stop_atr: 1.2, min_range_atr: 0.5, max_range_atr: 2.0}
# sweep only:
grid: {rr: [1.5, 2.0, 2.5], stop_atr: [0.8, 1.2, 1.6]}
# walkforward only:
walkforward: {train_months: 24, test_months: 6, objective: pf}
# propsim only:
propsim: {product: the5ers/hs50k_10d, source_job: J-20261101-001, runs: 500}
risk_profile: the5ers_hs50k_10d
```
`holdout` jobs are accepted only when `requested_by: validation`.
