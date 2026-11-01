# Prop Firm Manager

Read `AGENTS.md` first — its hard rules override everything. If you were started as an agent, your role file is
in `agents/` and your schedule is in `agents/SCHEDULE.md`.

- Python 3.11+; install with `pip install -r requirements.txt` (add `--break-system-packages` in the cloud sandbox).
- Tests: `python -m pytest -q`. Run them before committing code changes.
- Real market data lives only on the research PC (`data/` is git-ignored). In the cloud, queue a job ticket
  in `queue/pending/` instead of running real backtests; use `data: {synthetic: true}` only for smoke tests.
- Commit messages start with your role in brackets, e.g. `[research] add H-002`.
- Never commit secrets, account passwords or full account logins.
