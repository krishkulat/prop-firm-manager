id: H-006
title: Short gold through London and early New York after an Asian-session rise (XAUUSD)
written: 2026-11-04 by research (no open request; own run)
trials used before writing: 0. No backtest of this idea has been run. Nothing here came from looking at our data. No parameter was chosen from a result.

why this one now:
  - It tests the falling leg of the same day shape as H-003, but inside the current 13:30-21:00 IST window. C is blocked by Q-002 and D needs a new profile. This needs no owner decision.
  - Its evidence is gold-specific and includes costs, unlike H-004, which rests on analogy.

market reason:
  - Donati & Jung (2019): COMEX gold 2001-2018, 5-min bars. Gold rises in Eastern hours and falls for about nine hours after. In New York time, annualized cumulative return goes from 0% to 12.3% between 18:00 and 02:00, then falls to 0.9% at 10:00, and ends the day at 8.3%.
  - Their test of the falling leg, gross: -10.0% a year full sample, and for a short 9.5% / 7.1% / 13.5% in 2001-06 / 2007-12 / 2013-18. So it held in the bull market and in the flat period. Net of the full bid-ask spread: 6.2% in 2013-18; negative in the two earlier periods, when spreads were much wider.
  - Reading note: the thesis's Chapter 7 text swaps the Long and Short labels. I matched them by size: the -10.0% in section 1.4 is the 02:00-11:00 ET leg, and "Short" returns 10.0%. Inference, not stated in the thesis.
  - H1 2026 to June 26 (chart sourced to Bloomberg, ICE, WGC, in Caixin): Asia +12.97%, Europe -1.32%, US -15.08%. This confirms the figures H-003 quoted second-hand. Session boundaries are not given. **This period is inside our sealed holdout window.** It is a public figure used as motivation only, and no test or parameter here uses it.
  - Who is on the other side: Asian buyers who lift price in their own session and stop when it ends; Western sellers then find that price high against their own view. Donati & Jung report that East and West returns respond differently to the same macro shock, which fits two separate clienteles. Filtering on an Asian rise targets the days with something to give back, and is what makes this more than a flat short.
  - Why this could be wrong:
      - The thesis data ends in 2018. Nothing found tests 2019-2025, which is our research split. The 2026 figures cover one half-year.
      - Small effect. 10-13.5% a year is 4.0-5.4 bp a day, or about $0.80-1.07 on $2,000 gold, against our $0.85 round-trip cost. Unfiltered, this is about zero net. See "expected".
      - Short-only through a large gold bull market. Any year with a strong Western-hours trend will hurt.
      - The drop around the London fixes is part of this window and was strong only in the alleged manipulation years (their Fixing short: 2.7% / 16.6% / 3.5% gross). The electronic auction has run since 2015, so that part may be gone.
      - An Asian rise could continue instead. Intraday momentum is reported in Chinese metals futures, and Ma, Bouri, Xu, Zhou (2025) find both momentum and reversal in Shanghai gold and silver futures (abstract only, gold not separated).
      - We miss the first 1-2 hours of the leg, because entries start at 13:30 IST.

rules (plain words):
  - Asian rise R = (open of the 08:00 UTC M15 bar minus open of the 01:00 UTC M15 bar) / ATR(14) on the last completed H1 bar. 01:00 UTC is the SGE day open, the clock H-003 uses.
  - Signal: if R ≥ asia_rise_atr, go short. One trade a day, no re-entry. Short only.
  - Entry: open of the 08:00 UTC M15 bar. Fixed at 13:30 IST, the first bar the window allows, not tuned.
  - Stop: stop_atr × ATR(14, H1) above entry, visible SL placed with the order.
  - No profit target. Exit at exit_et (New York time) or at the stop. Default 11:00 ET is 20:30 IST in US summer time and 21:30 IST in winter, before flat-by 22:30 IST.
  - Minimum hold: no rule-based close inside 120 s (risk engine). The SL is attached at entry.
  - News: no entry or rule-based exit around high-impact news (firm rule). The backtest flattens before news per R-011 item 2a, so on NFP and CPI days the trade closes by 08:20 ET.
  - Banned methods: none used. One position, fixed stop, no adding.

parameters (≤ 4): 3
  - asia_rise_atr: 0.0-1.5 (default 0.5, the mirror of H-003's west_drop_atr default)
  - stop_atr: 1.0-3.0 (default 2.0, same as H-003, wide so costs stay a small share of 1R)
  - exit_et: {10:00, 11:00} (default 11:00, the end of the thesis's falling leg; 10:00 is its local low)
  Defaults were set from reasoning, before any run.

expected (rough guess, not a backtest):
  - About 30-40% of days qualify, or 80-105 trades a year, or about 530-710 on the research split.
  - Win rate 48-53%, average win and loss about equal (time exit, wide stop).
  - The stop is about $8 (scaled from H-004's ~$6 at 1.5 ATR), so cost is about 0.11R. PF 1.3 at an average absolute result near 0.6R needs about +0.08R net, or about +0.19R gross, which is $1.50 or 8 bp on $2,000 gold. That is roughly double the unfiltered 4-5 bp, so **the filter has to do most of the work**, and a failed baseline is the likeliest result.
  - Pace: at 90 trades a year, +0.08R is about 7R a year against the 30R the two challenge steps need at 0.5% risk. Passing `backtested` at the minimum would still be too slow. It needs about +0.15R to match D's 14R a year. Propsim decides this; do not relax it.

kill criteria (any one kills H-006):
  - Baseline at defaults (research split, news calendar loaded, backtest flattening before news): PF < 1.3 or trades < 200.
  - Random-direction benchmark: same entries and exits, random side. If H-006's avg R is not at least 0.10R above it, there is no directional edge.
  - No-filter benchmark (short every day, asia_rise_atr off): if that does as well or better, the "give back the Asian rise" reason is wrong. Record it and drop the idea; do not relabel it as a flat short.
  - Opposite-side result: if going long on the same signals does better, record it and stop. Do not relabel it: that needs a new hypothesis with the discovery disclosed, as with H-002.
  - Net R on days with no NFP or CPI release ≤ 0.
  - More than half of net R from one calendar year, or fewer than 5 of 7 years positive.
  - PF < 1.1 with slippage +50%; walk-forward OOS PF < 1.2; holdout PF < 1.1.

known problem for Strategy Dev and Backtest:
  - Same as H-004: the R-011 list holds FOMC, NFP and CPI only, and the EA flattens for every USD high-importance event in MT5. Here the effect is smaller, because a 10:00 ET release cuts a trade about 6 hours in, near the end of the leg, rather than 20 minutes in. An 08:30 ET release cuts more. The check against the full MT5 list is still needed before demo.

relation to other strategies: not derived from the Asian-range events; the signal is a fixed-clock return. Shares hours with B and D. On days Asia rises and London breaks the range high, B also sells, so check daily P&L correlation with B and E once runs exist and flag to the Orchestrator if above 0.5. E may hold the opposite side after a US-open rise. C's default exit (07:30 UTC) is before this entry; its 09:00 UTC option overlaps by an hour. One EA per account (Q-007) applies either way.

sources:
  - Donati, F. & Jung, J. A. (2019), "Gold Price Dynamics Around the Clock", MSc thesis, Copenhagen Business School (a thesis, not peer reviewed): https://research-api.cbs.dk/ws/portalfiles/portal/59803241/651553_Thesis_Contract_13383.pdf
  - Wang Shiyu, Caixin Global (2026-07-03), "Gold caught in a tug of war between Asian bulls and a hawkish Fed": https://www.caixinglobal.com/2026-07-03/analysis-gold-caught-in-a-tug-of-war-between-asian-bulls-and-a-hawkish-fed-102460438.html
  - Ma, Bouri, Xu, Zhou (2025), "The 'night effect' of intraday trading: Evidence from Chinese gold and silver futures markets", Global Finance Journal 64. Abstract only: https://www.sciencedirect.com/science/article/abs/pii/S1044028325000110
  - Jin, Kearney, Li, Yang (2020), "Intraday time-series momentum: Evidence from China", Journal of Futures Markets 40(4); metals, not gold: https://ideas.repec.org/a/wly/jfutmk/v40y2020i4p632-650.html
