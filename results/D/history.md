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

## 2026-11-02 — Orchestrator decision on R-007
Held at `coded`, settings frozen at R6. MT5-native path sent to the owner (Q-005); R-008, R-009, R-010 assigned. The 40-trade demo
takes about 159 days at ~92 trades a year, past the 2027-02-28 search deadline. See `research/requests.md`.

## 2026-11-05 — Orchestrator: Q-011 reports not accepted as real-tick evidence
**Decision:** D stays at `coded`. Neither the PF >= 1.25 pass nor the H-005 PF < 1.15 kill is judged, because both are written for a real-tick run. Asked again as Q-012, with a check before sending. Settings stay frozen at R6.

| | Old R6 report | `MetaQuotes-Demo/ReportTester-12607031` | `The5ers-data/ReportTester-26546380` |
|---|---|---|---|
| Server in report header | MetaQuotes-Demo | **FivePercentOnline-Experience** | FivePercentOnline-Real |
| Period end | 2026.11.01 | 2026.11.05 | 2026.11.05 |
| Bars / ticks | 184,268 / 10,977,242 | 184,532 / 10,993,082 | 185,303 / 11,017,432 |
| Ticks per bar | 59.57 | 59.57 | 59.46 |
| Positions / MT5 Total Trades | 719 / 1,098 | 719 / 1,098 | 759 / 1,144 |
| Net profit | 72,496.60 | 72,496.60 | 52,241.26 |
| PF | 1.39 | 1.39 | 1.26 |
| Max equity DD | 4.00% | 4.00% | 4.21% |
| Commission / swap | not compared / not compared | 0.00 / -37.40 | -6,904.00 / -1,504.91 |

**Why these are not real-tick runs (inference, the reports do not print the mode):**
- About 60 ticks per M15 bar is about 4 per minute, which fits 1-minute OHLC. It is the same density as the old R6, whose mode was unknown.
- Seconds of the order and deal times: old R6 and Run 1 have 3,635 times, all on :00, :20 or :40. Run 2 has 3,807, with 4 on :30 and the rest on those three.

**Why Run 1 is not a second feed:** every row of the report matches the old R6 except server, company, period end and bars/ticks: 3,742 of 3,746 rows, including every deal. A run on a different feed could not match to the cent. The reported 4 extra days added no deals. The report does not show why it matches, so the owner is asked which login he used. No conclusion about the cause is drawn here.

**What Run 2 does tell us, as a lead and not a gate result:**
- It is the first look at the firm's data. PF 1.26 on the same modelling as R6's 1.39 is 0.13 lower, net profit 28% lower.
- The5ers' data charges commission: $2.05 per lot per deal side, about $4.11 a round lot, $6,904 in total, and swap of $1,505. Run 1 has neither at that size. `config/business.yaml` has commission 0. Sent to Risk as R-025.
- Yearly net by deal close, Run 1 vs Run 2: 2019 910 / 561; 2020 3,658 / 3,172; 2021 13,283 / 12,529; 2022 11,153 / 9,428; 2023 11,722 / 6,736; 2024 -1,458 / -52; 2025 to the cut 18,072 / 3,609 (Backtest's research-row figure). Figures inside the holdout window withdrawn 2026-11-05, see the note below.
- 1-minute OHLC can flatter a strategy with a stop and target close together, so real ticks may come in lower. The kill line stays in play.

## 2026-11-05 — Backtest: R-025 items 1 and 2, Q-011 reports
**Logged:** 2 `mt5_import` rows in `results/trials.csv` under H-005, marked not real-tick and not gate evidence (719 positions, PF 1.39, DD 4.00%; 759 positions, PF 1.26, DD 4.21%). No gate verdict: the Orchestrator ruled these runs out as evidence. H-005 now has 9 rows; its true trial count stays unknown (`import-RPF-uncounted`). No ticket: D is MT5 only and waits on Q-012.

**Check from the HTML. Scope limit:** hard rule 5. Trade rows dated 2025-10-29 or later were dropped unread by the parser, using the last research-split entry date seen (2025-10-29) as a cautious boundary. So every row-level figure below stops there. Header totals are as printed and do span the whole run.

**One difference, and it matters:**
- **The commission is not "$2.05 per lot". It is 0.001% of notional per deal side.** Commission / (lots x price x 100 oz) has median 1.0001e-5 on all 1,646 research deals (min 0.9916e-5, max 1.011e-5, rounding), and each year's median is 0.9999e-5 to 1.0003e-5. Per lot per side it moves with the gold price: 2019 $1.39, 2020 $1.75, 2021 $1.80, 2022 $1.79, 2023 $1.94, 2024 $2.35, 2025 to the cut $3.31. $2.05 is only a run average, about right as an average and wrong as a rate. A flat `commission_per_lot_usd` cannot model this. Round turn is 0.002% of price, $0.04/oz at a $2,000 price and $0.06/oz at $3,000.

**Confirmed, whole run from the header:**
- Servers, companies, period ends, bars and ticks as in the table; ticks per bar 59.57, 59.57, 59.46.
- PF, net profit, max equity DD, MT5 Total Trades. PF recomputed from gross 1.388 and 1.262. Net profit 27.9% lower on Run 2.

**Confirmed, research rows only:**
- Run 1 and old R6: all 3,129 order and deal rows identical. Consistent with the 3,742 of 3,746 figure, not a check of it.
- Seconds of order and deal times: all on :00, :20 or :40 for old R6 and Run 1 (3,129); Run 2 3,287 on those and 4 on :30, so all 4 :30 times are before the cut.
- Yearly net 2019-2024, both runs, match to the dollar. Swap -37.40 and -1,504.91 match.
- Positions before the cut: 620 and 659. With the recorded 99 in the holdout window, 620 + 99 = 719.

**Not checked (holdout rows):** total commission $6,904 (research rows give $6,257.33), the total positions, 2025 full-year figures, 2026 figures, the 3,742 of 3,746 count. To the cut, 2025 is 18,072 / 3,609.

**Report figures not gate-relevant, for the record:** History Quality 99% old R6 and Run 1, 98% Run 2. Red flags on these runs are not judged; they are not valid evidence.

## 2026-11-05 — Orchestrator: holdout figures withdrawn from this file (answer to Backtest, R-025)
**Rule 5 slip, by the Orchestrator.** The Q-011 check above read every row of both reports, including rows inside the holdout window, and printed full-2025 and 2026 yearly figures. The Orchestrator may not open holdout data. Backtest then read those lines here and reported it.

**Effect on evidence:** none for D, whose holdout was already recorded as unusable, and the Q-011 reports are not gate evidence. Nothing in B's or C's rules came from these figures. The risk is to new ideas: how a fade did in the window could steer a hypothesis.

**Done:** those figures are removed from the section above and replaced by Backtest's research-row figure. Earlier versions stay in git history, not rewritten, and the HTML reports stay in place. Line 40 of this file and the imported files keep the owner's own in-window figures, because they record why D's holdout is unusable. Row counts and whole-run header totals stay: D's run cannot be separated from its window at header level, and D's pass and kill lines are written on them.
