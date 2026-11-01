# Agent schedule (Claude scheduled tasks)

Each line below becomes one Claude scheduled task. Every run starts a fresh session with this repo attached;
the prompt is the same shape for all agents. Times are IST.

| Agent | Schedule | Cron (CRON_TZ=Asia/Kolkata) |
|---|---|---|
| Orchestrator — hourly check | every hour | `0 * * * *` |
| Orchestrator — daily report | 23:30 daily | `23 23 * * *` |
| Orchestrator — weekly review | Sunday 10:00 | `41 9 * * 0` |
| Research | daily 07:00 | `52 6 * * *` |
| Strategy developer | daily 09:00 (works on assigned items only) | `43 8 * * *` |
| Backtest | every 4 hours (writes tickets, judges results) | `0 */4 * * *` |
| Validation | daily 20:00 | `47 19 * * *` |
| Risk & compliance | daily 12:00 | `49 11 * * *` |
| Capital | daily 22:00 + Sunday | `51 21 * * *` |
| Ops / release | daily 18:00 | `55 17 * * *` |

## Prompt template
```
You are the <ROLE> agent of the Prop Firm Manager business.
Repository: github.com/krishkulat/prop-firm-manager (clone it, work on main unless your role file says otherwise).
1. Read AGENTS.md, then agents/<role_file>.md. Follow them exactly; the hard rules override anything else.
2. Do one run of your job as described for this schedule slot (<SLOT>).
3. Commit with the prefix [<role>] and push. If nothing needed doing, commit nothing.
4. If the owner must act or decide, use `python -m pfm.reqs ...` (Capital/Ops) or write to
   results/reports/ and send a short Telegram summary via `python -c "from pfm import notify; notify.send('...')"`
   when TELEGRAM_* secrets are available; otherwise send a push notification.
Never buy, withdraw, deploy to a live account, loosen a risk limit, or open holdout data unless your role allows it.
```
