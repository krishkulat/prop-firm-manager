# Strategy A — history

- 2026-11-01 — Setup diagnostics on real XAUUSD M15 data (2019-01 → 2025-10 research split), run by hand outside
  the worker while checking the data export. **Count these as 2 trials of H-001.**
  - v1.0 defaults (range filter 0.5–2.0× H1 ATR): 58 signals in ~7 years; backtest halted at the 6% kill switch
    in 2020 after 17 trades. Diagnosis: the 05:30–12:30 IST range is 1.8–3.9× H1 ATR on 80% of days (median 2.67×),
    so the filter kept only 18% of days. Design error in the seed parameters, not a market finding.
  - Range filter 1.5–4.0×: 451 signals; still halted by the kill switch in 2019 after 21 trades (PF 0.14).
    Diagnosis: research backtests must not use the challenge kill switch. Fixed in the worker (research mode:
    no kill, no throttle; the kill switch is tested in propsim).
  - Cost note: average stop ≈ $2.33 vs ≈ $0.67 round-trip cost (spread + 0.30 slippage per side) → costs ≈ 29% of
    1R. Tight-stop variants are structurally disadvantaged under our conservative cost model.
- 2026-11-01 — v1.1: range filter defaults 1.5/4.0, sweep ranges rescaled. Baseline job J-20261101-001 updated to
  v1.1 defaults; it will be the first full-period research backtest.
- 2026-11-01 — [orchestrator] J-20261101-001 (v1.1 baseline, research split, research mode): **backtested gate FAIL** —
  426 trades, PF 0.23, win rate 13.1%, maxDD 146.5%, every year −17% to −28%. Stage stays `coded`, redesigns stay 0.
  Not rejected yet: a 13% win rate with targets averaging +1.67R and stops −1.07R is far below what random entries
  would give (~35% before costs), so this looks like an implementation bug (direction/target/timezone) rather than a
  market finding. Code audit requested as R-002. Trials used on H-001: 3 / 50.
- 2026-11-01 — **Verdict J-20261101-001 (v1.1 baseline, rr 2.0 / stop_atr 1.2 / range 1.5–4.0×): FAIL `backtested`.**
  Research split 2019-01 → 2025-10, M15, research mode (no kill switch). Judged by backtest agent.
  | metric | result | gate | |
  |---|---|---|---|
  | trades | 426 | ≥ 200 | pass |
  | PF | 0.23 | ≥ 1.3 | FAIL |
  | maxDD (0.5% risk, non-compounded) | 146.5% | ≤ 6% | FAIL |
  | worst year | −27.6% (2019) | ≥ −5% | FAIL |
  | PF with slippage +50% | 0.21 | — | already failing |
  Every year 2019–2025 lost −17% to −28%; this is not one bad year. Win rate 13.1%, avg −0.70R, Sharpe −4.5.
  Exits: 356 stop / 53 target / 17 session end. Longs (236) avg −0.73R, shorts (190) avg −0.66R — both sides fail.
  - **Red flag — win rate far below chance.** With target 2R and stop 1R a random entry would hit target first
    ~33% of the time (≈24% after our ~0.29R cost load). 12.4% target hits is far worse than random. Either the
    breakout systematically reverses (a real fade effect) or the backtest has a bias (e.g. stop placed on the
    wrong side of the range, stop-first assumption on bars that touch both levels). Needs a code check before
    any more trials are spent — covered by the Orchestrator's R-002. If the code is correct, a fade of this
    range would be a new hypothesis for Research, not a sweep of H-001.
  - **Red flag — fast stop-outs.** 29 trades exit within 15 min (28 stops) and 93 within 60 min (89 stops).
    Check the same-bar fill logic, and the firm's minimum trade duration, before propsim.
  - Stop exits show MAE median 1.16R, max 3.59R (bar extremes beyond the stop); stop fills average −1.07R, so
    fills look consistent with costs. Realised target R averages 1.67R, not 2.0R (costs ≈ 0.3R per trade, matches
    the cost note above).
  - Minor: `yearly_pct` lists 2018 (0.0) though data starts 2019; `news_calendar_loaded: false`; the worker's
    trials.csv timestamp for this job (08:22) is earlier than the manual diagnostics (08:30–08:35).
  - Concentration and parameter-cliff checks not applicable (no profit; single parameter set).
  - **Next:** no sweep queued. A sweep on a PF 0.23 baseline is very unlikely to reach PF 1.3 honestly and would burn
    trials (3 of 50 used for H-001). Waiting for R-002 (code audit).
