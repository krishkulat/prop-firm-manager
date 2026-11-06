id: H-002
title: Asian-range false-breakout fade at the London open (XAUUSD)
written: 2026-11-02 by research (answers R-001 / R-003 item 1)

disclosure (read first):
  - **Discovery run void (Q-010, added 2026-11-06).** The audit-R002-2 run below used the look-ahead in `breakout_events`, so this idea's origin is not evidence of an edge. It stays counted as a trial. Tagged lines cite that run. No rule, default or kill criterion changed. Next evidence is B v1.0 on fixed code (R-022, Q-010 decision).
  - This idea was FOUND ON THE RESEARCH SPLIT, not derived from theory first. The R-002 audit
    (`results/A/history.md`, run "audit-R002-2") flipped strategy A's 426 breakout signals to the opposite
    direction: n 426, win 49.8%, avg +0.22R, target hits 38.7% (2019-01 → 2025-10, M15, 30-pt slippage). [CONTAMINATED, Q-010]
  - **Trial count starts at 1** (that audit run). Parameter defaults below are A v1.1's defaults, i.e. exactly
    the audited run, chosen before looking at anything else. No parameter was picked from that run.
  - Do not judge H-002 on that same run again. Evidence must come from walk-forward OOS, then the sealed holdout.

market reason:
  - Asian hours on spot gold are thin; the 05:30–12:30 IST range collects resting stop orders just beyond its
    high and low. When London liquidity arrives, the first push through the range triggers those stops; dealers
    and London participants absorb that flow and price returns into the range once the stops are filled
    (a "liquidity sweep"). The counterparty of the fade is the stopped-out Asian-session trader and late
    breakout buyers/sellers.
  - Caution: in FX, Osler (2002) found stop-loss cascades make prices trend *further* after round numbers, i.e.
    the textbook microstructure story supports breakouts, not fades. Our only evidence for the fade is
    in-sample. Gold volatility rises 12:00–14:00 GMT (Batten et al. 2017), so the window is also the noisiest
    part of the day — fills and slippage matter.

rules (plain words):
  - Range = high/low of 05:30–12:30 IST on completed M15 bars (same window and code path as strategy A).
  - Range filter: trade only if range width is within [min_range_atr, max_range_atr] × ATR(14) on H1.
  - Signal: first M15 close beyond the range between 13:30 and 16:30 IST. One signal per day.
  - Entry: at the open of the next M15 bar, in the OPPOSITE direction to the break
    (close above range high → sell; close below range low → buy).
  - Stop: stop_atr × ATR(14, H1) from entry, on the breakout side (visible SL, placed with the order).
  - Target: rr × risk. One target rule only; a range-midpoint exit is a possible later redesign, not part of v1.
  - Time exit: flat by 22:30 IST. No overnight holds.
  - Minimum hold: never close by rule within 60 s of entry (The5ers `min_trade_seconds: 60`); with M15
    bar-based exits this is automatic, but the EA must enforce it for intrabar SL/TP too. Note that A had
    29 of 426 trades close within 15 min — still above the firm's 60 s, but check the fade's distribution. [CONTAMINATED, Q-010]
  - News: skip entries and do not close by rule within ±2 min of high-impact news (firm rule); the backtest
    must run with the news calendar loaded (A's baseline ran with `news_calendar_loaded: false`).

parameters (≤ 4):
  - rr: 1.0–2.5 (default 2.0)
  - stop_atr: 0.8–2.0 (default 1.2)
  - min_range_atr: 1.0–2.0 (default 1.5)
  - max_range_atr: 3.0–5.0 (default 4.0)
  Cost note: at default stops the cost load is ~0.29R per trade (≈ $0.67 cost vs ≈ $2.33 stop). Wider
  stop_atr lowers the cost share; that is the main reason to sweep stop_atr, not to hunt for a better PF.

expected (from the in-sample run only — not a forecast):
  - ~1.2 trades/week (426 in ~6.8 years), win rate 45–50%, R:R 1:2 before costs, ≈ 1:1.7 after. [CONTAMINATED, Q-010]
  - Expect walk-forward OOS to come in materially worse than +0.22R/trade because of selection. [CONTAMINATED, Q-010]

kill criteria (any one kills H-002):
  - Baseline at defaults on the research split with news calendar loaded: PF < 1.3 or trades < 200.
  - Walk-forward OOS PF < 1.2, or OOS DD > 1.5× in-sample.
  - PF < 1.1 with slippage +50% (edge is just cost-model optimism).
  - More than half of net R comes from one calendar year, or fewer than 5 of 7 years are positive.
  - Longs and shorts disagree in sign (a one-sided result in a 2019–2025 gold bull market is trend beta,
    not a fade edge).
  - Holdout PF < 1.1 (Validation, once).

relation to other strategies: mirror of rejected A/H-001 by construction (same signal times). Expected to be
  uncorrelated with H-003 (different hours, no range signal).

sources:
  - Internal: `results/A/history.md` (J-20261101-001 and R-002 audit table, 2026-11-01). [CONTAMINATED, Q-010]
  - Osler, C. L. (2002), "Stop-Loss Orders and Price Cascades in Currency Markets", FRBNY Staff Report 150:
    https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html
  - Batten, Lucey, McGroarty, Peat, Urquhart (2017), "Stylized facts of intraday precious metals", PLoS ONE
    12(4): e0174232: https://reading-clone.eprints-hosting.org/79175/1/BattenLuceyMcGroartyPeatUrquhart2017.pdf
