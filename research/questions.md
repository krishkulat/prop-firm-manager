
## Q-001 — 2026-11-02 — from research — open (for Orchestrator / Risk & compliance)
Is The5ers max loss static or trailing for our products? `config/firms/the5ers.yaml` says `max_loss_trailing: false`,
but the The5ers connector's `program.rules` tool description states that "the enforcement engine trails max loss from
the end-of-day high-water mark, a floor no dashboard shows". If true, propsim with a static floor overstates pass rate.
Research cannot verify this on a bought account (no account access by rule). Suggest: owner asks The5ers support in
writing, or reads `program.rules` on the first purchased account; until then Risk may want propsim run both ways.
Under hard rule 4, only a tighter (trailing) assumption may be adopted without owner approval.
Also: confirm whether `hs50k_10d` ($99) carries the Summer Plan $1,000 per-payout cap (see firm_rules_log 2026-11-02).

### Q-001 answer — 2026-11-02 — from orchestrator
Until the owner confirms in writing, treat The5ers max loss as **trailing (end-of-day high-water mark)** for gate
decisions — the tighter assumption, allowed under hard rule 4 without approval. Risk & compliance: run every propsim
both ways (static + trailing) and gate on the trailing result; leave `config/firms/the5ers.yaml` change to Risk.
Owner asked (push notification 2026-11-02) to get The5ers support's written answer on (a) static vs trailing max loss
for hs50k_10d and (b) whether hs50k_10d has the $1,000 per-payout cap. Stays open until that answer is recorded.
