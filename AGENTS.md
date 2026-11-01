# AGENTS.md — shared rules for every agent

This repository IS the business. Every agent reads this file first, then its own role file in `agents/`.

## Mission
Turn a $250 account reserve into a self-funding portfolio of funded prop accounts, trading XAUUSD with
deterministic MT5 bots, while keeping the probability of losing the reserve as low as possible.

## Hard rules (no agent may break these)
1. **No money actions.** Agents never buy, withdraw, transfer or log in to a firm. The Capital agent writes a
   purchase request; the owner buys.
2. **No live deployments.** Agents never touch the live VPS or a live account. The Ops agent writes a deploy
   request; the owner deploys.
3. **No AI in the live order path.** Live bots are compiled MQL5 EAs with the shared risk engine
   (`mql5/Include/PFM/RiskEngine.mqh`). Nothing calls an LLM to place an order.
4. **Risk limits only go down.** Any change that loosens `config/risk/*.yaml` or a firm mapping needs an
   owner approval recorded in `requests/`.
5. **Sealed holdout.** Data dated inside `holdout` in `config/business.yaml` is read only by the Validation
   agent, once per strategy version. Everyone else uses `pfm.data.load(..., split="research")`.
6. **Count every trial.** Every backtest run is appended to `results/trials.csv` by the worker. Max
   `max_trials_per_hypothesis` per hypothesis. No deleting rows.
7. **Firm rules win.** Banned everywhere: HFT, tick scalping, latency/hedge arbitrage, grid, martingale,
   copying other people's signals, hidden stop-losses, trades shorter than the firm minimum.
8. **No secrets in the repo.** Tokens live in `.env` (git-ignored) or OS credential stores.
9. **Business stop-loss** in `config/business.yaml` is final. If hit, the Orchestrator stops all purchase
   requests and tells the owner.

## How agents work together
- **Shared memory = this repo.** Write what you did, why, and the evidence. Small commits, clear messages,
  prefixed with your role: `[research] add hypothesis H-007 london fade`.
- **Job queue.** Heavy compute is a YAML ticket in `queue/pending/`. The worker on the research machine
  runs it and moves it to `queue/done/` (or `queue/failed/`) with results in `results/<job_id>/`.
  Ticket format: see `queue/README.md`.
- **Strategy registry.** `strategies/registry.yaml` holds every strategy's stage. Only the Orchestrator
  changes `stage`, and only when the gate evidence is in `results/`.
- **Owner requests** go in `requests/` as YAML and are sent to Telegram by `pfm.notify`. The owner
  replies `/bought <id> <login>`, `/deployed <id>`, `/paid <id> <amount>` or `/reject <id> <reason>`.

## Pipeline stages and gates (from config/business.yaml → gates)
`idea → coded → backtested → walkforward → holdout → propsim → demo → release → live → retired`

| Gate | Passed by | Owner of the check |
|---|---|---|
| backtested | trades ≥ 200, PF ≥ 1.3, maxDD ≤ 6% at 0.5% risk, no year worse than −5% | Backtest |
| walkforward | out-of-sample PF ≥ 1.2, OOS DD ≤ 1.5× in-sample | Backtest |
| holdout | holdout PF ≥ 1.1, holdout DD ≤ 1.5× in-sample, deflated Sharpe > 0 | Validation |
| propsim | pass ≥ 30%, breach ≤ 40% on exact firm rules | Backtest + Risk |
| demo | 10+ trading days, 0 rule breaches, trade rate ±30% of backtest, slippage ≤ 1.5× assumed | Validation |
| release | risk review signed in `results/<strategy>/release_review.md` | Risk & compliance |

## Writing style
Facts, numbers, dates, file links. No hype. If unsure, say so and open a question for the Orchestrator in
`research/questions.md`.
