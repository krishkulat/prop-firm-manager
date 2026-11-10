# Running a PFM EA in the MT5 Strategy Tester (R-014)

Read this before any MT5 tester run of B, C or E, and before comparing a tester result with a Python backtest.

## 1. Time base: the three tester inputs are required

In the Strategy Tester `TimeGMT()` equals the simulated server time
(https://www.mql5.com/en/docs/dateandtime/timegmt), so an EA cannot find GMT by itself there.
`mql5/Include/PFM/TimeBase.mqh` takes the broker's offset from three inputs (group "PFM time base"):

| Input | Meaning | Typical GMT+2/+3 server (New York close) |
|---|---|---|
| `InpTesterGmtWinterMin` | server minus GMT in winter, minutes | `120` |
| `InpTesterGmtSummerMin` | server minus GMT in summer, minutes | `180` |
| `InpTesterDstRule` | when the server changes: `PFM_DST_NONE`, `PFM_DST_US`, `PFM_DST_EU` | `PFM_DST_US` |

- **Find the values on the broker's own terminal**, not from this table: in a live/demo chart of that server,
  compare the Market Watch server clock with UTC on a winter date and a summer date, and note on which weekend it
  changed (US: 2nd Sunday of March / 1st Sunday of November; EU: last Sunday of March / October).
- **Unset or invalid → the run does not start.** B, C and E fail `OnInit` with "PFM time base: set ...".
  Any other EA on the risk engine (A, F) still starts but every order is rejected with `time_base_unset`.
  Valid means: a rule is chosen, both offsets are whole quarter hours within ±14 h, and `PFM_DST_NONE` has
  winter = summer.
- **Outside the tester** these inputs are ignored. Live/demo uses the terminal's clocks, the offset rounded to
  15 min, as before R-014.
- The one server hour that repeats when the server falls back (a Sunday, gold closed) is read as summer time.
- Tester logs show `PFM time base (tester): winter ..., summer ..., rule ...` at start. Copy that line into the
  job's result notes.

## 2. News: the filter is OFF in every tester run

`PfmNewsBlackout()` returns `false` whenever `MQL_TESTER` is set, because the MT5 economic calendar is not
available in the tester. So in a tester run:

- no entry is blocked for news (`news_blackout` never appears), and
- no open position is flattened before a news event (`news` close never appears).

The Python backtester does apply the news calendar (`research/news/usd_high_impact.csv` or `data/news.csv`).
**A tester result is therefore not news-flat and must not be read or filed as news-flat.** Before comparing a
tester run with a Python run, either compare against a Python run with an empty news calendar, or drop the
Python trades closed with reason `news` and the days whose entry was rejected `news_blackout`, and say which.
Every tester result written to `results/` states: `news filter: off (MT5 tester)`.

## 3. Still needed before any tester run

- A **MetaEditor compile** of the EA with the current `mql5/Include/PFM/` files. Nothing here has been compiled
  in MetaEditor; the cloud has no MT5. The time arithmetic is tested by compiling the `PFM-TIME` block of
  `TimeBase.mqh` with a C shim (`tests/test_time_base.py`).
