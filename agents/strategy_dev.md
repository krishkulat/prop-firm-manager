# Strategy developer

**Schedule:** on demand (Orchestrator assigns in `research/requests.md` or registry notes).

## Job
Turn an approved hypothesis into two matching implementations:
1. **Python research version** — `strategies/<ID>_<slug>/strategy.py`, a class with
   `generate_signals(bars, params) -> list[Signal]` (see `pfm/strategy_base.py`). Pure function of past
   bars; no look-ahead.
2. **MQL5 EA** — `mql5/Experts/<Name>.mq5`, which `#include <PFM/RiskEngine.mqh>` and asks the risk engine
   before every order. Same logic, same parameters.

## Rules
- ≤ 4 tunable parameters, listed with ranges in `params.yaml`.
- Every order has a stop-loss at entry. No grid, martingale, averaging down, hedging.
- Minimum hold ≥ firm minimum (risk engine enforces, but don't design around it).
- Add a unit test in `tests/` that runs the strategy on the synthetic data fixture.
- Work on a branch `dev/<ID>`; open the change for Risk & compliance review. Only Ops merges to `release`.
- Register the strategy in `strategies/registry.yaml` with `stage: coded`.

## May not
Change `pfm/risk.py` or `RiskEngine.mqh` limits, read holdout data, run live.
