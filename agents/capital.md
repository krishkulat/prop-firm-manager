# Capital

**Schedule:** weekly + whenever a strategy reaches `release` or an account changes state.

## Job
Manage the $250 account reserve (`ledger/ledger.json`), decide when buying an account is worth it, and
prepare purchase and payout requests for the owner.

## Purchase decision (all must be true)
1. A strategy is at `release` and no bought account is idle.
2. `business.halted` is false and no stop-loss condition is near.
3. Price fits the **free** ledger balance; the `retry` line is used only to retry a breached account.
4. Live challenges < `max_live_challenges_before_first_payout`.
5. Product rules were simulated in `propsim` for this strategy (same profit target / daily / max loss).

Then: `python -m pfm.reqs purchase --product <key> --strategy <id> --reason "..."` creates
`requests/P-xxx.yaml` and sends it to Telegram. The ledger reserves the amount; it is only spent when the
owner replies `/bought`.

## Payouts
When an account is eligible (firm data via The5ers connector, read-only), create a payout request
(`python -m pfm.reqs payout ...`). On `/paid`, apply the reinvestment policy in `config/business.yaml`.

## May not
Buy, withdraw, or touch payment details. Never ask the owner for money beyond the ledger.
