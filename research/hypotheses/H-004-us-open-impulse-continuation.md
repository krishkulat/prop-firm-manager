id: H-004
title: US-open impulse continuation (XAUUSD)
written: 2026-11-03 by research (answers R-005 item 2)
trials used before writing: 0. No backtest of this idea has been run. Nothing here came from looking at our data. No parameter was chosen from a result.
Q-010 mark (research, 2026-11-06): lines tagged [CONTAMINATED, Q-010] cite figures made by the look-ahead in `breakout_events`. They stay as written and are not evidence. No rule, default or kill criterion changed.

market reason:
  - The 08:30 New York hour is when US data lands and the US session starts. Gold futures volatility responds most to employment reports,
    GDP, CPI and personal income among 23 US announcements (Cai, Cheung, Wong 2001). After FOMC shocks gold keeps adjusting past the first five minutes
    (Awartani, Hussain, Virk 2024).
  - Intraday momentum is documented elsewhere: the first half-hour of SPY predicts the last half-hour, more strongly on volatile days and some macro news days (Gao, Han, Li,
    Zhou; R² about 2%). Across 60+ futures, commodities included, returns up to the last half-hour predict that half-hour (Baltussen, Da, Lammers, Martens 2021). In Chinese metals futures the effect is
    strongest in high-volume and high-volatility sessions (Jin, Kearney, Li, Yang 2020).
  - Who is on the other side: traders who react late, plus hedgers who must buy after rises and sell after falls (short-gamma hedging in the Baltussen account). A large first-hour move is
    where those flows should be largest. The impulse filter targets that.
  - Why this could be wrong:
      - No paper found tests this on gold at the US open. Everything above is by analogy, and the published effect sits in the last half-hour of a session. Our flat-by rule forces us out before the COMEX close, so we cannot hold that window.
      - Our own A/B evidence shows breakouts reversing at the London open. That was a different hour and signal, so it does not test this idea, but it is a reason for doubt. [CONTAMINATED, Q-010]
      - Donati & Jung (2019) find gold tends to fall in Western hours, so the long side may lose and the short side may just be that drift. The sign test below covers this.

rules (plain words):
  - All times are New York time, so DST follows the US data clock.
  - Impulse I = (close of the 09:15 ET M15 bar, i.e. price at 09:30 ET, minus open of the 08:30 ET M15 bar) / ATR(14) on the last completed H1 bar.
  - Signal: if |I| ≥ impulse_atr, trade in the direction of I. One trade a day, no re-entry.
  - Entry: open of the 09:30 ET M15 bar. This is 19:00 IST in US summer time and 20:00 IST in US winter time, inside the 13:30-21:00 IST window.
  - Stop: stop_atr × ATR(14, H1) from entry, visible SL placed with the order.
  - No profit target. Exit at exit_et or at the stop. Default 11:30 ET is 21:00 or 22:00 IST, before flat-by 22:30 IST.
  - Minimum hold: no rule-based close inside 120 s (risk engine). The SL is attached at entry.
  - News: no entry or rule-based exit around high-impact news (firm rule). An 08:30 release ends its blackout at 08:45, so it does not block the 09:30 entry.
  - Banned methods: none used. One position, fixed stop, no adding.

parameters (≤ 4): 3
  - impulse_atr: 0.5–1.5 (default 1.0)
  - stop_atr: 1.0–2.5 (default 1.5). Wide on purpose, so costs stay a small share of 1R.
  - exit_et: {10:30, 11:00, 11:30} (default 11:30). 12:00 ET is left out because it equals the 22:30 IST flat-by in US winter time.
  Defaults were set from reasoning, before any run.

expected (rough guess, not a backtest):
  - The share of days with |I| ≥ 1.0 is unknown; a guess of 20-35% gives 50-90 trades a year, or about 350-620 on the research split. A count under 200 kills the idea.
  - Win rate 40-48%, average win larger than average loss (time exit, no target). The cost model is about $0.85 round trip, which is 0.14R on a $6 stop, so the real cost share has to be read from the first baseline.

kill criteria (any one kills H-004):
  - Baseline at defaults (research split, news calendar loaded, backtest flattening before news per R-011 item 2a): PF < 1.3 or trades < 200.
  - Random-direction benchmark: same entry times and exits, random side. If H-004's avg R is not at least 0.10R above it, there is no directional edge.
  - Opposite-side result: if fading the same signals does better, record it and stop. Do not relabel it as a fade: that needs a new hypothesis with the discovery disclosed, as with H-002.
  - No-filter benchmark (impulse_atr = 0): if that does as well or better, the "large impulse" reason is wrong.
  - Longs and shorts disagree in sign (one side is trend beta or the Western-hours drift).
  - Net R on days with no NFP or CPI release ≤ 0. Those releases fall on about 10% of days, too few to carry a strategy.
  - More than half of net R from one calendar year, fewer than 5 of 7 years positive, or 2019-2023 net negative.
  - PF < 1.1 with slippage +50%; walk-forward OOS PF < 1.2; holdout PF < 1.1.

known problem for Strategy Dev and Backtest:
  - **Live EA flatten rule.** 10:00 ET releases such as ISM are not in `research/news/usd_high_impact.csv`. If the MT5 calendar rates them high importance (not checked), the EA would flatten at 09:50 ET on those days, 20 minutes after entry, so the
    live trade would differ from the backtest and pay full costs for almost no hold. The backtest with the R-011 list will overstate how often the full hold happens. A check with the full MT5 event list is needed before demo,
    or the trade-rate gate is likely to fail. If those days must be skipped, the trade count falls and the 200 minimum has to be rechecked.
  - The London PM auction (15:00 London, usually 10:00 ET) falls inside the hold. Caminschi & Heaney (2014, data 2007-2012, old fix) found drift for about 12 minutes from the start of the fix, then little change for the rest of the hour. This is noise for H-004, not part of the signal.

relation to other strategies: not derived from the Asian-range events. Signal is a fixed-clock return, not a range break. It runs later than B's entries (latest 11:00 UTC) but B can still be open, so check daily P&L correlation with B and D once
  runs exist; flag to the Orchestrator if above 0.5. Two open positions at 0.5% fit `max_open_positions: 2` and `max_open_risk_pct: 1.0`. No time overlap with C (exits by 09:00 UTC at the latest).

sources:
  - Cai, Cheung, Wong (2001), "What moves the gold market?", Journal of Futures Markets 21(3): https://scholars.hkbu.edu.hk/en/publications/what-moves-the-gold-market/
  - Awartani, Hussain, Virk (2024), "How do the gold intra-day returns and volatility react to monetary policy shocks?", IRFA 95: https://pure.kfupm.edu.sa/en/publications/how-do-the-gold-intra-day-returns-and-volatility-react-to-monetar/
  - Gao, Han, Li, Zhou, "Intraday Momentum: The First Half-Hour Return Predicts the Last Half-Hour Return". Read through a summary only, the paper itself could not be opened: https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/
  - Baltussen, Da, Lammers, Martens (2021), "Hedging demand and market intraday momentum", JFE 142(1): https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html
  - Jin, Kearney, Li, Yang (2020), "Intraday time-series momentum: Evidence from China", Journal of Futures Markets 40(4): https://ideas.repec.org/a/wly/jfutmk/v40y2020i4p632-650.html
  - Caminschi & Heaney (2014), "Fixing a Leaky Fixing", Journal of Futures Markets 34(11): https://api.research-repository.uwa.edu.au/ws/files/4725264/A0205_use_this.pdf
  - Donati & Jung (2019), "Gold Price Dynamics Around the Clock": https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/
