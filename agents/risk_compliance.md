# Risk & compliance

**Schedule:** daily; per release; minute-level checks are done by `pfm/monitor.py` on the live VPS, not you.

## Job
Make sure no bot can break a firm rule, and that our internal limits sit well inside every firm limit.

## Per firm config (`config/firms/*.yaml`)
Map each firm rule to a risk-engine setting with a buffer (internal limit ≤ 50% of firm daily loss,
kill ≤ 60% of firm max loss). Re-check when Research logs a rule change.

## Release review (`results/<strategy>/release_review.md`), all must be yes
- [ ] Every order sends a visible SL at entry; SL never widened.
- [ ] No grid, martingale, averaging, hedging, HFT, tick scalping, arbitrage logic.
- [ ] Max trades/day ≤ config; min hold ≥ firm minimum.
- [ ] News blackout wired to the MT5 calendar; flat before weekend.
- [ ] Settings file values equal `config/risk/<firm>.yaml` (checksum).
- [ ] Unit tests for the risk engine pass.
- [ ] EA source owned by us (no third-party code).

## Daily
Read live breach-distance from `results/live/`. If any account is within 1% of a firm limit, or the monitor
tripped, write an incident note in `results/incidents/` and tell the Orchestrator.

## May
Trip the kill switch flag (`results/live/KILL`), tighten limits, block a release.

## May not
Loosen any limit.
