# USD high-impact news calendar (R-011 item 1)

`usd_high_impact.csv`: columns `time` (UTC, ISO 8601) and `event`. 251 rows, 2019-01-04 to 2026-10-28. `load_news` needs only `time`.

| Event | Rows | Time (New York) | Source |
|---|---|---|---|
| `NFP` (Employment Situation) | 93 | 08:30 | BLS archive, dates from the release file names: https://www.bls.gov/bls/news-release/empsit.htm |
| `CPI` | 93 | 08:30 | BLS archive, same method: https://www.bls.gov/bls/news-release/cpi.htm |
| `FOMC` (scheduled statement) | 62 | 14:00 | Fed calendars below, decision day = last day of the meeting |
| `FOMC_unscheduled` | 3 | as released | Fed press releases below |

FOMC sources: https://federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2026),
https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm and https://www.federalreserve.gov/newsevents/pressreleases/2020-press-fomc.htm (2020),
https://www.federalreserve.gov/newsevents/pressreleases/monetary20180525a.htm (2019 tentative dates).

The event list was fixed from the firm-rule purpose (R-011). No market data was read and no event was chosen by its effect on any strategy.
New York time is converted to UTC with `America/New_York`, so US DST is handled: 08:30 is 12:30 or 13:30 UTC, 14:00 is 18:00 or 19:00 UTC.

## Dates worth knowing
- **Shutdown changes:** Oct 2025 NFP and CPI were never published (no row). Sep 2025 CPI came on 2025-10-24, Sep 2025 NFP on 2025-11-20, Nov 2025 NFP on 2025-12-16,
  Nov 2025 CPI on 2025-12-18, Jan 2026 NFP on 2026-02-11, Jan 2026 CPI on 2026-02-13. All rows use the actual date, not the original schedule.
- **2020:** the 17-18 Mar meeting was cancelled. Three unscheduled statements: 2020-03-03 10:00 EST, 2020-03-15 17:00 EDT (a Sunday, market closed), 2020-03-23 08:00 EDT. Times are from the Fed press releases
  ([03-03](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm), [03-15](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm), [03-23](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323a.htm)).

## Left out
FOMC minutes, press conferences, the 2019-10-11 reserve-management announcement, notation votes with no rate statement (2020-03-19, 2020-03-31), and the longer-run goals statements of 2020-08-27 and 2025-08-22.

## Known limits
1. **Gap against the live EA (R-011 note).** The EA flattens for every USD high-importance event in the MT5 calendar. This file holds FOMC, NFP and CPI only, so any other event the MT5 calendar rates high importance (for example ISM, PCE, GDP or retail sales, not checked here) is absent. The backtest will
   flatten less often than the EA. The list stays fixed for B's baseline.
2. **Times are the scheduled clock times.** Each scheduled FOMC row assumes 14:00 ET. That time was read directly only in the October 2019 minutes (`fomcminutes20191030.htm`); the other rows rely on the Fed's standing practice.
3. **Checks done:** counts per year (12 each 2019-2024; 11 in 2025; 10 so far in 2026), weekdays (non-Friday NFP dates are only the July 3 holiday-week cases and the shutdown dates; non-Wednesday FOMC dates are only 2020-11-05, 2024-11-07 and the unscheduled rows).
   No second independent source was compared row by row.
4. **Stops at 2026-10-28.** Anyone extending it should add new releases as they occur. Next on the BLS schedule: CPI on 2026-11-10.
