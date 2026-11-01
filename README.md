# Prop Firm Manager

An AI-agent-run prop trading business. Eight Claude agents research, build, test and manage XAUUSD trading
bots for prop-firm accounts (The5ers first), around the clock. The owner does two things only, when asked:
**buy accounts** and **deploy bots**. Starting account reserve: **$250**.

> Prop challenges are hard: about 14% pass and about 7% of buyers ever get paid (industry data, 2025–26).
> The system's first job is to prove an edge on research data before any money is spent. No profit is promised.

## How it works
```
Claude agents (scheduled, cloud) ──read/write──► this GitHub repo ◄── worker on research PC (backtests, demo)
         │                                                ▲
         └── Telegram requests ──► owner ──buys / deploys─┤
                                                          └── live VPS: MT5 + approved EA + monitor (no AI)
```
- `AGENTS.md` — hard rules and how agents cooperate. `agents/*.md` — one file per agent role.
- `agents/SCHEDULE.md` — when each agent runs (Claude scheduled tasks).
- `config/` — business rules and gates, firm products, risk profiles.
- `ledger/ledger.json` — the $250 account reserve (changes only on owner-confirmed events).
- `strategies/` — registry + strategy code. `research/` — hypotheses. `queue/` — job tickets.
- `results/` — every job's output, `trials.csv` (every test ever run), reports, live status.
- `pfm/` — Python: risk engine, backtester, prop-challenge simulator, walk-forward, worker, requests, Telegram, monitor.
- `mql5/` — the shared MQL5 risk engine and EAs that run live.

## Owner commands (Telegram)
`/bought <id> <login>` · `/deployed <id>` · `/paid <id> <amount>` · `/breached <account>` · `/funded <account>` ·
`/reject <id> <reason>` · `/status` · `/kill`

## Setup — research PC (build phase)
1. Install Git, Python 3.11+, MetaTrader 5; open a free **demo** account (XAUUSD available).
2. `git clone https://github.com/krishkulat/prop-firm-manager.git` and `cd prop-firm-manager`.
3. PowerShell: `scripts\setup_windows.ps1` (creates venv, installs packages, copies EA files to MT5, runs tests).
4. Telegram: talk to @BotFather → `/newbot` → put the token in `.env` as `TELEGRAM_BOT_TOKEN`; send your bot a
   message, open `https://api.telegram.org/bot<token>/getUpdates`, copy `chat.id` into `TELEGRAM_CHAT_ID`.
5. Export data: `.venv\Scripts\python -m pfm.data export --symbol XAUUSD --timeframe M15 --start 2019-01-01`.
6. Start the worker: `scripts\run_worker.bat`. Keep the PC on and awake (Power settings → Sleep: Never).

## Developer commands
```
python -m pytest -q                                   # tests
python -m pfm.worker --once --no-git                  # run one queued job locally
python -m pfm.reqs list                               # open owner requests
python -m pfm.release package --strategy A --version 1.0 --profile the5ers_hs50k_10d --ea GoldBreakout_A
```

## Known limits
- Backtests run on M15 bars with conservative fills (stop first if both levels touched in one bar). Confirm
  promising strategies in the MT5 Strategy Tester on real ticks before the demo stage.
- The news filter in backtests needs `data/news.csv` (UTC times of high-impact USD events); live EAs use the
  MT5 calendar.
- The prop simulator re-sizes trades in risk units and assumes trades don't overlap.
- Firm rules change; `config/firms/` must be re-checked (Research agent, weekly) and before every purchase.

Not financial, legal or tax advice. Indian residents: see the business plan's India section and consult a CA.
