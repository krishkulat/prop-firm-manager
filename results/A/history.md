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

## 2026-11-01 — Code audit for R-002 (by the setup session, on the research PC data, research split only)
**Verdict: no implementation bug found. The 13% win rate is a real market effect: the breakout reverses.**

Same 426 signal times as J-20261101-001, same stop distance and 2R target, only the direction changed
(research risk mode, 30-point slippage):

| Variant | n | win rate | avg R | target hits |
|---|---|---|---|---|
| Breakout (as coded) | 426 | 13.1% | −0.70 | 12.4% |
| Opposite direction (fade) | 426 | 49.8% | +0.22 | 38.7% |
| Random direction (seed 0) | 426 | 32.4% | −0.22 | 26.8% |
| Breakout, zero slippage | 426 | 13.8% | −0.60 | 12.4% |

- The random-direction run lands where theory predicts for a 1R stop / 2R target after costs (~25–33%), so fills,
  stop/target placement and the stop-first rule are not biasing results. Breakout and fade are mirror images.
- Checked: entry is at the open of the bar AFTER the signal bar (Signal.time = signal bar close); H1 ATR uses
  completed H1 bars only; session window in IST is correct after c3d358b (weekly open verified at Sun 22:00 UTC
  summer / 23:00 UTC winter); long/short stop and target sides are correct.
- Not checked here: Python vs MQL5 equivalence on identical bars (do this before any EA reaches demo).
- **Trials:** these 4 audit runs are logged in results/trials.csv. The fade result was found by looking at research
  data, so any fade hypothesis starts with 1 trial already spent and must not be judged on this same run alone.

**Recommendation to the Orchestrator:** reject H-001 / strategy A (no bug; the edge points the other way).
Ask Research to write the fade as its own hypothesis (H-002, "London-open false-breakout fade"), with the above
as the motivating in-sample observation, and push it through walk-forward → sealed holdout → propsim like any other.
- 2026-11-01 — [orchestrator] **Stage → `rejected`.** Failed `backtested` (J-20261101-001: PF 0.23, maxDD 146.5%, all years −17% to −28%); R-002 audit found no implementation bug. Not sent back as a redesign: the evidence says the breakout premise is wrong, not its parameters. The fade observation goes to Research as a separate hypothesis (H-002 via R-001), with the in-sample discovery disclosed. Final H-001 trial count: 7 rows in trials.csv.

- 2026-11-05 — [orchestrator] **Q-010: the figures above are contaminated by look-ahead.** `breakout_events` let the 23:45 IST bar into the range. J-20261101-001, the manual-diag rows and the R-002 audit rows stay counted as trials but are not evidence. The R-002 "no bug" finding and the "systematic reversal" reason are withdrawn. Stage stays `rejected` until one clean baseline at the same defaults (H-001's trial 8, after R-022): passes the whole `backtested` gate → `coded`; otherwise the rejection stands on clean figures. See `research/questions.md`.

- 2026-11-10 — [orchestrator] **Rejection stands on clean figures. H-001 closed.** J-20261109-001 (A v1.2, defaults, fixed code 5f43fae, news calendar loaded and covering the data) failed `backtested`: PF 0.719 < 1.3, maxDD 98.57% > 6%, worst year −31.25% < −5% (989 trades, win 32.8%, avg −0.194R, 0 of 7 years positive, stress-slip PF 0.645). No redesign. Look-ahead red flag: none; a losing result is the opposite of what look-ahead produces.
