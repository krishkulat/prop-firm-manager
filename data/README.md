# Market data (git-ignored)

Put XAUUSD bars here as `XAUUSD_M15.csv` (and optionally `XAUUSD_M1.csv`).
Columns: `time,open,high,low,close,spread` — `time` in UTC (`YYYY-MM-DD HH:MM:SS`), `spread` in points.

Export from your MT5 terminal on the research PC:
```
python -m pfm.data export --symbol XAUUSD --timeframe M15 --start 2019-01-01
```
(uses the MetaTrader5 Python package; your demo terminal must be open and logged in).

The last `holdout_months` (config/business.yaml) are sealed: `pfm.data.load(split="research")` cuts them off.
