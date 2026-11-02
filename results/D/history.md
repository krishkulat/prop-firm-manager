# Strategy D: RangeProfileFadeEA (imported) — history

## 2026-11-02 — Imported and evaluated (setup session)

**Source:** owner's separate Claude session. Hand-over, EA source, six MT5 Strategy Tester reports and per-position
CSVs are in `research/imported/RangeProfileFadeEA/`. The extra report the owner attached
(`reports/R6_MT5_StrategyTester_report.html`) is R6 again (identical net profit 72,496.60).

**Verdict: promising, not ready.** The edge looks real but thin, it was tuned on all the data we have, and the EA
as written would break two The5ers High Stakes rules. It needs a real-tick re-run, three compliance fixes and a
forward demo before any purchase. It is the strongest candidate in the pipeline today.

### 1. What the owner's session established (from the hand-over; MT5, MetaQuotes-Demo, XAUUSD M15, 2019-01 → 2026-10)

| Run | Change | Positions | Win % | PF | Max equity DD | Worst year |
|---|---|---|---|---|---|---|
| R1 | first EA (server time wrongly assumed UTC) | 793 | 37.2 | 1.10 | 16.35% | 2019 −7.3% |
| R2 | time zone + DST, min stop 4× spread | 743 | 39.4 | 1.18 | 8.79% | 2020 −3.4% |
| R3 | Friday flat 20 UTC, broker session end | 737 | 39.3 | 1.20 | 10.79% | 2020 −3.5% |
| R4 | block entry hour 09 UTC | 708 | 40.1 | 1.24 | 7.99% | 2020 −2.4% |
| R5 | holiday rule + partial at POC/1.0R 50% + BE | 732 | 58.1 | 1.34 | 4.50% | 2024 −0.7% |
| R6 | partial 1.25R, 60% | 719 | 56.6 | 1.39 | 4.00% | 2024 −1.0% |

Learnings carried over from that session:
- Deviation **fade** beat breakout and retest entries in an early multi-timeframe grid (numbers not retained).
- Most of the improvement R1 → R4 came from **correct time handling** (server GMT+2/+3 with US DST), not from
  new entry logic. The same class of bug we fixed in our data export (commit c3d358b).
- The partial exit + break-even (R5/R6) roughly halved drawdown and raised win rate from ~40% to ~57%.
- 2024 was the only losing year in R6 (PF 0.95); 2019 and 2020 were weak.
- Bugs found and fixed there: ATR method (SMA vs Wilder) changed which ranges qualified; time zone; weekend and
  holiday holds; tiny stops dominated by spread.

### 2. Independent checks done here (from the R6 report's deal list; 719 positions, net reconciles to the cent)

| Check | Result | Meaning |
|---|---|---|
| Extra round-trip cost +$0.20/oz | PF 1.38 → **1.18** | Thin edge: median stop is only $3.29/oz (10% of stops < $1.39) |
| Extra cost +$0.40/oz | PF **1.01** (break-even) | Our standard cost model adds $0.60/oz → PF 0.87. MT5 report does not say what spread/modelling was used |
| 2019-01 → 2025-10 | PF 1.36, n 620 | — |
| 2025-11 → 2026-10 (our holdout window) | PF 1.47, n 99 | **Not out-of-sample**: settings were chosen on this period too |
| Worst IST day | −2.99R (−1.5% at 0.5% risk) | Inside the 3% daily limit; fine |
| Positions with a close < 60 s after entry | **13** (3 fully closed < 60 s; 28 < 120 s) | **Breaks The5ers 60-second minimum trade duration** |
| Entries inside our risk profile window (13:30-21:00 IST) | 325 of 719 | EA trades round the clock; needs its own profile (same question as Q-002 for C) |
| News filter | none | **High Stakes bans opening/closing within 2 min of high-impact news** |
| Sizing | 0.5% of current balance, compounding (lots up to 12.96) | Prop accounts: size from initial balance via the PFM risk engine |

### 3. Challenge fit (pfm.propsim, The5ers $50K High Stakes 10% D, firm limits, static max loss, 400 runs, cap 3 years)

| Risk per trade | Extra cost | Pass | Breach | Not finished in 3 y | Median days to pass |
|---|---|---|---|---|---|
| 0.5% | none | 84% | 0% | 16% | 617 |
| 0.5% | +$0.20 | 33% | 0% | 67% | 833 |
| 0.75% | none | 92% | 0% | 8% | 414 |
| 0.75% | +$0.20 | 72% | 4% | 24% | 603 |
| 1.0% | none | 97% | 0% | 3% | 307 |
| 1.0% | +$0.20 | 76% | 19% | 5% | 396 |

The EA rarely breaches but is **slow**: +0.15R per trade × ~92 trades/year ≈ 14R/year, while the 10% + 5% steps
need 30R at 0.5% risk. With our default 180-day horizon every run is "unfinished". MAE was not in the report, so
every trade was assumed to reach −1R intrabar (conservative). Trailing max loss (Q-001/R-006) not modelled yet.

### 4. Trial count and validation status
- Logged in `results/trials.csv` under H-005: 6 rows for R1-R6, plus 1 row flagging the uncounted work.
- Uncounted: the owner's neighbour runs (number unknown) and a browser grid of up to 41,040 configurations.
  A deflated-Sharpe adjustment with an honest trial count cannot be computed; treat the in-sample PF as optimistic.
- **Our sealed holdout is not usable for D** (the owner tuned on 2019-2026). Out-of-sample evidence must come from:
  (a) a different broker's history (e.g. The5ers' own feed), unchanged settings; and (b) a forward demo.

### 5. What D needs before the Capital agent may consider it (proposed; Orchestrator decides)
1. **Real-tick re-run** of R6 in the MT5 Strategy Tester ("Every tick based on real ticks"), with the spread
   recorded, on MetaQuotes-Demo AND on the prop firm's MT5 data. Gate: PF ≥ 1.25 on both, no settings changed.
2. **v1.30 compliance build** (Strategy Dev, review by Risk): include `PFM/RiskEngine.mqh`; no partial or full
   close before 120 s; USD high-impact news blackout; size from initial balance; internal daily stop and kill
   switch; keep all v1.22 trading logic and inputs unchanged.
3. **Its own risk profile** (round-the-clock entries with a daily break 21:00-23:00 UTC) — owner decision, same
   as Q-002 for C.
4. **Challenge maths**: with this edge a 2-step challenge takes 10-20 months. Capital should compare products
   (e.g. fewer steps or lower target) and risk 0.75% vs 1% before any purchase request.
5. **Forward demo** of v1.30 on the research PC: ≥ 40 trades, PF ≥ 1.0, DD ≤ 10R.
6. Note correlation with B (both fade failed breakouts): do not run B and D on the same account at full risk.
