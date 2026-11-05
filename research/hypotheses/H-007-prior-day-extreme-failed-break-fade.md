id: H-007
title: Failed break of the prior day's high or low, faded inside 13:30-21:00 IST (XAUUSD)
written: 2026-11-05 by research (answers R-020)
trials used before writing: 0 on these rules. No backtest of this rule has been run and no market data was read. Disclosure: the idea is motivated by research-split results of A, B and D (see "evidence"), so those results are not independent evidence for it. Dollar figures below come from the existing trade list of J-20261103-005 (arithmetic only, no trial).

why this one now:
  - After E and F, the only entries in this book with a positive result are failed breaks (B, D). Fixed-clock direction lost in both directions.
  - The side here comes from an event: price went through a level and came back. It does not come from a clock return.
  - It uses a level set before the session, not the Asian range. It needs no owner decision: all entries are inside the risk window.

market reason:
  - Who is on the other side: stops and breakout entries resting beyond the prior day's extremes. When price trades through, those orders fill as market orders. If no real buyer or seller follows, the flow is spent and price returns. We provide liquidity after the run, against traders who are now caught.
  - Osler (2003; NY Fed Staff Report 150): on FX order data, stop-loss orders cluster just beyond round levels and take-profit orders at them. Rates reverse more often at take-profit clusters (59.3% vs 54.8% at arbitrary levels, dollar-mark; 60.1% vs 57.3%, dollar-yen).

evidence, including what cuts against it:
  - In-house, same family: A's breakouts won 13% of trades against 32% for random entries (R-002). B's clean baseline J-20261103-005: 426 trades, PF 1.407, avg +0.205R, net $1.75/oz, median stop $4.64. D's R6: PF 1.39, about $0.45/oz of cushion before PF reaches 1.0, interpolated (PF 0.89 at +$0.60, 1.04 at +$0.40). All in-sample and selected.
  - Against: Osler also finds that a **crossing** tends to continue, for at least two hours, and reversals last under 30 minutes. That is FX and round numbers, not gold. The reclaim rule below is what is meant to separate an absorbed run from a cascade. It is untested.
  - Against: no gold paper on prior-day extremes was found. Trading-forum material on "liquidity sweeps" was ignored. The closest gold test, Quantex 2026-10-18 (not peer reviewed, daily bars, 2005-2024), finds round $100 levels held **less** often than other levels (45.0% vs 49.2%, first touches). Round numbers are not this level, but it is a warning that levels may not be special on gold. The `shifted_level` benchmark tests exactly this.
  - Against: Grant, Wolf, Yu (2005): large intraday reversals in stock index futures are significant, but significance drops sharply after transaction costs.

rules (plain words):
  - Day = 17:00 to 17:00 New York time. PDH and PDL = high and low of the last completed day on M15 bars.
  - Level is live only if no bar has traded beyond it since that day ended. A level taken out in Asia is dead for the day. This is what makes the level different from the Asian range.
  - Break: an M15 bar with a time in 08:00-15:00 UTC trades beyond a live level by at least 0.10 × ATR(14, H1), fixed, about the cost of a round trip, so a tick through does not count.
  - Ignore a break whose bar starts within 60 minutes after an NFP or CPI release: that move is information, not a stop run. Fixed.
  - Reclaim: within reclaim_bars M15 bars, counting the break bar, a bar closes back inside the level.
  - Entry: open of the next M15 bar, against the break (PDH broken and reclaimed → sell; PDL → buy). One trade a day, first valid signal only, no re-entry. Last entry bar opens 15:15 UTC (20:45 IST).
  - Stop: stop_atr × ATR(14, H1) from entry, visible SL placed with the order. If the break's extreme is already beyond that stop, skip the trade, because the stop would sit inside the move that defines the signal.
  - Target: target_r × risk.
  - Time exit: 16:30 UTC (22:00 IST), before flat-by 22:30 IST.
  - Minimum hold: no rule-based close inside 120 s (risk engine). SL attached at entry.
  - News: as H-004 and H-006, with the backtest flattening before news (R-011 item 2a).
  - Banned methods: none used. One position, fixed stop, no adding.

parameters (≤ 4): 3
  - reclaim_bars: {1, 2, 4} (default 2. 1 = wick only, 4 = one hour)
  - stop_atr: 1.0-2.0 (default 1.25, about $4.70 at the $3.75 median ATR implied by F's stops, which keeps the cost share near B's)
  - target_r: 1.0-2.5 (default 2.0, the R:R that the estimate below borrows from B)
  Defaults were set from reasoning, before any run.

expected (rough guess, not a backtest):
  - Frequency: my guess, no data read. A fresh level break in the window on about 30-35% of days, reclaimed in time on about 60% of those, so about 35-60 trades a year, or 240-400 on the research split. The gate needs 200, so this could fail on count alone.
  - Cost: $0.85 round trip on a $4.70 stop is about 0.18R.
  - Edge: net $/oz in the family runs from D's about $0.45 to B's $1.75. Both are selected. My central guess is $1.00, which is a discount on B and is a judgement, not a measurement.
  - Net: **about +0.21R a trade central, +0.10R at D's figure, +0.37R at B's.** The central case clears R-020's +0.15R. The low end does not.
  - Win rate 44-50% at 1:2 before costs. Needed for +0.21R with all trades reaching stop or target: about 46%.
  - Pace: at 50 trades a year, +0.21R is about 10R a year, against D's 14R and the 30R the two challenge steps need at 0.5% risk. Propsim decides this; do not relax it.
  - Drawdown: B failed the gate on maxDD in a long losing stretch. Expect the same risk here; this family has no short-run diversifier.

kill criteria (any one kills H-007):
  - Baseline at defaults (research split, news calendar loaded, backtest flattening before news): PF < 1.3 or trades < 200.
  - `random_side`: same entries and exits, random side. If H-007's avg R is not at least 0.10R above it, there is no directional edge. Use more than one seed if the worker allows, since E and F showed one seed is noisy.
  - `shifted_level`: same rules with levels moved outward by 0.25 × prior-day range. If that does as well or better, the prior-day level is not the reason. Record it and drop the idea; do not relabel it.
  - `no_reclaim`: fade the first break at the next bar open. If that does as well or better, the reclaim reason is wrong. Record and drop.
  - `opposite_side`: if continuation does better, record it and stop. Relabelling needs a new hypothesis with the discovery disclosed, as with H-002.
  - **Not B again:** against J-20261103-005 (and B v1.1 when it exists), if more than 50% of H-007's trade days are also B trade days on the same side, or daily P&L correlation is above 0.5, it adds no diversification. Flag to the Orchestrator and do not take it further as a separate strategy. Overlap is likely on 08:00-11:00 UTC days, because a live PDH sits above the Asian high, so a PDH break is also an Asian-range break.
  - Net R on days with no NFP or CPI release ≤ 0.
  - More than half of net R from one calendar year, or fewer than 5 of 7 years positive. Long and short avg R of opposite sign.
  - PF < 1.1 with slippage +50%; walk-forward OOS PF < 1.2; holdout PF < 1.1.

known problems for Strategy Dev and Backtest:
  - Same as H-004 and H-006: the R-011 list holds FOMC, NFP and CPI only, and the EA flattens for every USD high-importance event in MT5. Check against the full list before demo. The 60-minute break exclusion uses the R-011 list.
  - M15 bars cannot show the order of a break and an intrabar stop. 21 of B's 426 trades in its first run closed within 15 minutes, so count entry-bar stops and report them, as for B and E.
  - The day boundary uses New York time, so DST must follow `America/New_York`, as E does. Do not read holdout data when checking this.

relation to other strategies: same mechanism as B and D, different events. Not derived from the Asian-range events, but overlapping them is possible and is a kill criterion above. E, F are rejected. C's default exit is before this window. One EA per account (Q-007) applies.

sources:
  - Osler, C. (2003), "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", Journal of Finance 58(5): https://econpapers.repec.org/RePEc:bla:jfinan:v:58:y:2003:i:5:p:1791-1819
  - Osler, C., "Stop-loss orders and price cascades in currency markets", NY Fed Staff Report 150: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf
  - Osler, C. (2000), "Support for resistance: technical analysis and intraday exchange rates", FRBNY Economic Policy Review 6(2). Abstract only: https://fedinprint.org/item/fednep/19790
  - Grant, Wolf, Yu (2005), "Intraday price reversals in the US stock index futures market: A 15-year study", Journal of Banking and Finance 29(5). Abstract only: https://researchwith.montclair.edu/en/publications/intraday-price-reversals-in-the-us-stock-index-futures-market-a-1/
  - Vu, H. X., Quantex Research (2026-10-18), "Do round numbers matter for gold?", not peer reviewed: https://quantex.com.sg/research/2026-10-18-gold-round-numbers/
  - In-house: `results/A/history.md`, `results/B/history.md`, `results/D/history.md`, `results/J-20261103-005/`.
