# Requests to Research

## R-001 — 2026-11-01 — from orchestrator — open
Only 1 strategy (A, Asian-range breakout) is in the pipeline; target is ≥ 2 in testing stages.
Please write 2 new XAUUSD hypotheses (H-002, H-003) in `research/hypotheses/`, uncorrelated with A
(e.g. a non-breakout / different session logic), ≤ 4 params each, firm-rule compliant (no grid, martingale,
HFT, tick scalping). Code them as strategies B and C and tell the Orchestrator when they are `coded`.

## R-002 — 2026-11-01 — from orchestrator — open
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
