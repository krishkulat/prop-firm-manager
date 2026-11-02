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

## 2026-11-02 — Backtest verdict on J-20261102-001: FAIL `backtested`, not a valid baseline

B v1.0, rr 2.0 / stop_atr 1.2 / range 1.5-4.0x, research split, M15, research mode (no kill switch). Agrees with the Orchestrator's decision above.

| metric | result | gate | |
|---|---|---|---|
| trades | 426 | ≥ 200 | pass |
| PF | 1.427 | ≥ 1.3 | pass |
| maxDD (0.5% risk, % of initial) | 8.52% | ≤ 6.0% | **FAIL** |
| worst year | -2.99% (2019) | ≥ -5.0% | pass |
| `news_calendar_loaded` | false | required by H-002 | **invalid baseline** |

Yearly %: 2019 -2.99, 2020 +8.67, 2021 +8.27, 2022 +11.71, 2023 +5.87, 2024 +2.31, 2025 +12.33. Win rate 49.8%, avg +0.221R, Sharpe 1.18.
Exits: 201 stop, 165 target, 60 session end. Last exit 2025-10-29.

**Role-file red flags**
- Parameter peak: not testable, one parameter set.
- Profit from one month: not flagged. Best month 2025-09 is 9.6% of net (limit 40%).
- Slippage +50%: PF 1.282. Not a collapse and above H-002's 1.1 kill line, but below 1.3.
- Spread +50%: **not tested by the worker**, it stresses slippage only. Estimate from the trade list, charging +$0.125/oz per trade (assumes 25-pt spread): PF ≈ 1.36; with slippage +50% as well, PF ≈ 1.22. The same method gives 1.273 for slippage alone against the worker's 1.282, so treat these as approximate. Arithmetic on `trades.csv`, no market data read, no trial.

**H-002 kill criteria on this run (none fired; run is not the valid baseline)**
- Largest year 2025 = 26.9% of net R (limit 50%). 6 of 7 years positive (minimum 5).
- Longs +54.2R (n 190, avg +0.285), shorts +40.0R (n 236, avg +0.170): same sign.

**Other flags**
- **Drawdown is a long losing stretch, not one bad day.** 2023-08-18 to 2024-02-05: 29 trades, -16.56R. Longest losing streak 8. On the gate's basis (% of initial) closed trades alone give **8.24%**, so intraday lows add only 0.28 points.
- **Correction to the 6.04% closed-trade figure** in `results/reports/daily/2026-11-02.md` and the section above: that is the same stretch as % of peak equity, not % of initial. Reaching 6.0% needs the news filter to remove about 2.5 points, roughly 5R, of that stretch. See Q-006.
- **Weak recent edge before 2025:** 2024 made +4.8R, and shorts lost -2.2R in 2023. 2025 alone is +25.3R.
- **Entry-bar stops (Q-002 item 2 reporting):** 9 of 426 trades hit the SL in the entry bar, all stops, -9.7R total. 21 closed within 15 min and 60 within 60 min. M15 bars cannot show whether any closed in under 60 s.
- Same numbers as audit-R002-2, so this is not independent evidence for the edge. `yearly_pct` lists an empty 2018, as in A's run.

**Trials:** H-002 has used 2 of 50 (audit-R002-2, logged under H-001, and this job). `trials.csv` shows 1 row under H-002.

**Next:** no ticket queued. R-011 steps 1 and 2 are not on `main` (`research/news/` is absent, `load_news` still reads only `data/news.csv`), so a run now would repeat this job and spend a trial for nothing. Queue the clean baseline once both land. No sweep, walk-forward or propsim until the gate passes.
