id: H-003
title: Long gold during the Shanghai Gold Exchange day session, after a Western-hours sell-off (XAUUSD)
written: 2026-11-02 by research (answers R-001 / R-003 item 2)
trials used before writing: 0 (no backtest of this idea has been run; A's diagnostics touched the same hours
  only to measure range width, not returns)

market reason:
  - Physical and retail gold demand is concentrated in China and India (2025: >50% of global bar and coin
    demand per WGC data cited in the MoneyMetals article below). Chinese buyers trade on the Shanghai Gold
    Exchange day session, 09:00–15:30 Beijing = 01:00–07:30 UTC = 06:30–13:00 IST (no DST in China).
  - Several sources report gold rising in Eastern hours and falling in Western hours:
    Donati & Jung (2019, CBS thesis) find a hat-shaped intraday pattern, up in Eastern hours and down for the
    rest of the day, profitable before costs (Sharpe up to 1.61) but weak after costs. The WGC H1 2026 summary
    (as quoted by MoneyMetals) reports +12.9% in Asian hours vs −15% in North American hours. Bouri, Ma, Xu,
    Zhou find Chinese-session predictability in SGE/SHFE gold futures (small, R² ≈ 0.6%).
  - Who is on the other side: Western futures/CFD sellers whose moves in NY hours are partly reversed when
    price-sensitive Asian physical buyers step in at a lower price ("buy the dip" on SGE open). The conditional
    filter (enter only after Western hours fell) targets exactly that reversal and is what makes this more than
    "be long gold in a bull market".
  - Main risk: the unconditional pattern is largely gold's 2019–2025 uptrend showing up in one session. The
    test must beat a time-matched benchmark (see kill criteria), not just be positive.

rules (plain words):
  - Western-hours return W = close at 21:00 UTC minus close at 13:30 UTC of the previous trading day
    (NY + late London), measured in units of ATR(14) on H1 at 21:00 UTC.
  - Signal: if W ≤ −west_drop_atr, go long at the open of the 01:00 UTC M15 bar (06:30 IST).
    (west_drop_atr = 0 means "any Western-hours decline".)
  - Stop: stop_atr × ATR(14, H1) below entry (visible SL with the order).
  - No profit target. Exit at exit_utc (default 07:30 UTC = SGE day close = 13:00 IST), or at the stop.
  - Long only (the hypothesis is about Asian buying; a short side is a separate idea).
  - Skip SGE holidays (no day session). News: no entry or rule-based exit within ±2 min of high-impact news
    (firm rule); otherwise news inside the holding window is not filtered.
  - Hold time is 6.5 h by design, so the 60 s minimum trade duration is not an issue except for stop-outs
    on a gap at entry — the EA must not close by rule within 60 s.
  - Exits at 07:30 UTC are before H-002's earliest entry (13:30 IST = 08:00 UTC), so the two never overlap.

parameters (≤ 4):
  - west_drop_atr: 0.0–1.5 (default 0.5)
  - stop_atr: 1.0–3.0 (default 2.0) — wide on purpose: costs (~$0.85 round trip incl. 0.30 slippage per side)
    must stay a small share of 1R.
  - exit_utc: {07:30, 09:00} (default 07:30; 09:00 tests whether the effect carries into early London)
  Only 3 parameters; the entry time is fixed by the SGE schedule, not tuned.

expected (rough, from the literature, not a backtest):
  - With the 0.5 ATR filter, perhaps 1–2 trades/week (~40% of days have a meaningful Western-hours drop).
  - Win rate 50–55%, small average win/loss ratio ~1 (time exit, wide stop). Edge, if any, is small per
    trade; cost load is the main threat.

kill criteria (any one kills H-003):
  - Baseline at defaults (research split, news calendar loaded): PF < 1.3 or trades < 200.
  - Benchmark test: the same rules entered at a random hour of the same days with the same hold length and
    stop must do clearly worse. If H-003's avg R is not at least 0.10R above the random-hour benchmark,
    the result is trend beta, not a session effect.
  - Filter test: run once with no W condition (long every SGE day, same stop/exit) as a benchmark. If that
    does as well or better, the "reversal of Western selling" reason is wrong — record it and drop the idea
    rather than re-labelling it as an unconditional long.
  - Fewer than 5 of 7 years positive, or 2019–2023 (before the 2024–2025 rally) net negative.
  - Walk-forward OOS PF < 1.2; PF < 1.1 with slippage +50%; holdout PF < 1.1.

relation to other strategies: different hours (Asian), different signal (prior-session return, no range
  breakout), long only. Expect low correlation with H-002; check daily P&L correlation once both have runs.

sources:
  - Donati, F. & Jung, J. A. (2019), "Gold Price Dynamics Around the Clock", MSc thesis, Copenhagen Business
    School: https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/
  - Bouri, Ma, Xu, Zhou, "Night trading momentum and determinants of predictability: Evidence from Chinese
    metal futures market": https://acfr.aut.ac.nz/__data/assets/pdf_file/0008/686816/4a-Z-Ivy-Zhou.pdf
  - MoneyMetals (2026-07-12), "A Strange Dichotomy: Gold Up on the Year in Asian Markets, Down Big in the West"
    (opinion piece; quotes WGC H1 2026 session data — verify against the WGC original):
    https://www.moneymetals.com/news/2026/07/12/a-strange-dichotomy-gold-up-on-the-year-in-asian-markets-down-big-in-the-west-005059
  - Shanghai Gold Exchange trading hours: https://en.sge.com.cn/eng_trading_ProductsIntroduce
  - Batten et al. (2017), PLoS ONE 12(4): e0174232 (intraday volume/volatility shape of spot gold).
