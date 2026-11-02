# Strategy B: Asian-range false-breakout fade — history

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
- Fails only maxDD → Orchestrator chooses one redesign (counts toward the 3) or rejection. Closed-trade DD alone was 6.04%, so the news filter would have to help for it to pass.
- PF < 1.3 or trades < 200 → H-002 kill criterion: rejected.
- Lowering risk below 0.5% to pass is not allowed: the gate is defined at 0.5% risk.
