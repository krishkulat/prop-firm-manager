id: H-001
title: Asian-range breakout at the London open (XAUUSD)
market reason: Gold trades thinly in the Asian session; when London liquidity arrives, orders cluster beyond
  the overnight range and price often extends in the breakout direction.
rules (plain words):
  - Range = high/low of 05:30–12:30 IST.
  - Enter on an M15 close beyond the range between 13:30 and 16:30 IST; one trade per day.
  - Skip if range width is outside [0.5, 2.0] × ATR(14) on H1.
  - Stop = range midpoint or stop_atr × ATR(14, H1) from entry, whichever is tighter.
  - Target = rr × risk. Flat by 22:30 IST.
parameters (≤ 4):
  - rr: 1.5–2.5 (default 2.0)
  - stop_atr: 0.8–1.6 (default 1.2)
  - min_range_atr: 0.3–0.7 (default 0.5)
  - max_range_atr: 1.5–2.5 (default 2.0)
expected: ~3–4 trades/week, win rate 38–45%, R:R 1:2
kill criteria: PF < 1.3 on 2019–(holdout start) with real spread, or results depend on one year.
sources: session-based range breakout is a long-standing, widely documented intraday idea; verify, don't trust.
