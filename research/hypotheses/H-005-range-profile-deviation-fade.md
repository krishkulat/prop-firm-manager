id: H-005
title: Range Profile deviation fade (imported EA "RangeProfileFadeEA" v1.22, XAUUSD M15)
origin: Built and tested by the owner in a separate Claude session (2026-11-01/02), imported 2026-11-02.
  Full hand-over: research/imported/RangeProfileFadeEA/HANDOVER.md. Evaluation: results/D/history.md.
Q-010 mark (research, 2026-11-06): lines tagged [CONTAMINATED, Q-010] cite figures made by the look-ahead in `breakout_events`. They stay as written and are not evidence. No rule, default or kill criterion changed. D's own MQL5 results are not touched by the bug.
market reason: Inside an established intraday range (swing-detected, edges stable within 0.3 ATR), a close
  outside an edge that quickly closes back inside is a failed breakout; stops beyond the edge have been taken and
  price tends to rotate back into the range. Same family as H-002 (London fade) and the R-002 finding that
  Asian-range breakouts on XAUUSD reverse far more often than chance. [CONTAMINATED, Q-010]
rules (plain words, v1.22):
  - Range: last 4-10 alternating swing pivots (3 bars each side), >= 2 highs and 2 lows, highs within 0.6 ATR of
    each other and lows likewise, height 1-6 ATR, span >= 8 bars. ATR = 14-bar SMA of true range.
  - Signal: a close outside an edge (deviation), then the first close back inside -> trade the opposite way.
  - Stop: deviation extreme + 0.1 ATR. Target: 2R. Partial: 60% at the range volume POC if >= 0.3R away, else
    at 1.25R; then stop to break-even.
  - Filters: no entries 09:00-09:59 UTC; stop >= 4x spread; flat 20:55 UTC (Fri 20:00, holidays 16:00);
    no entries 21:00-23:00 UTC. One position at a time. 0.5% of balance per trade (compounding).
parameters: 54 inputs; the range engine values were never changed in MT5. Choices made on the reported data:
  blocked hour 9, partial mode/R/%, holiday rule, Friday flat hour.
expected (in-sample, MT5 R6): ~92 trades/year, win rate 56.6%, PF 1.39, avg +0.15R, max equity DD 4.0% at 0.5%.
kill criteria: PF < 1.15 on a real-tick re-run with realistic spread; any firm-rule violation that cannot be
  removed; forward demo PF < 1.0 after 40 trades or drawdown > 10R.
trials: NOT countable. 6 MT5 reports, an unknown number of owner neighbour runs, and a browser grid of up to
  41,040 configurations (executed count unknown). The 2019-2026 history, including our holdout window, was used
  for tuning, so there is no untouched holdout for this hypothesis. See results/D/history.md.
sources: "Range Profile Structure [BOSWaves]" indicator (MPL-2.0), ported by the owner's session.
