
## Q-001 — 2026-11-02 — from research — open (for Orchestrator / Risk & compliance)
Is The5ers max loss static or trailing for our products? `config/firms/the5ers.yaml` says `max_loss_trailing: false`,
but the The5ers connector's `program.rules` tool description states that "the enforcement engine trails max loss from
the end-of-day high-water mark, a floor no dashboard shows". If true, propsim with a static floor overstates pass rate.
Research cannot verify this on a bought account (no account access by rule). Suggest: owner asks The5ers support in
writing, or reads `program.rules` on the first purchased account; until then Risk may want propsim run both ways.
Under hard rule 4, only a tighter (trailing) assumption may be adopted without owner approval.
Also: confirm whether `hs50k_10d` ($99) carries the Summer Plan $1,000 per-payout cap (see firm_rules_log 2026-11-02).
