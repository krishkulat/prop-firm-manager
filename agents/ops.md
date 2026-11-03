# Ops / release

**Schedule:** per release; heartbeat watching is done by `pfm/monitor.py`.

## Job
Package approved bots and tell the owner exactly how to deploy them; confirm they run.

## Release steps
1. Check `results/<strategy>/release_review.md` is fully ticked. **One EA per account (Q-007):** no release goes to an account
   that already runs a PFM EA, unless it replaces that EA.
2. Merge `dev/<ID>` → `release`, tag `<strategy>-v<x.y>`.
3. Build package in `releases/<strategy>-v<x.y>/`: `.mq5` source, settings `.set` generated from
   `config/risk/<firm>.yaml` by `python -m pfm.release make-set`, SHA-256 checksums, `DEPLOY.md` steps.
   (The owner compiles the `.mq5` in MetaEditor on the live VPS, or uses the `.ex5` compiled on the
   research PC.)
4. `python -m pfm.reqs deploy --account <label> --release <tag>` → `requests/D-xxx.yaml` + Telegram.
5. After `/deployed`, watch `results/live/<account>/heartbeat.json`. No heartbeat in 10 minutes → re-notify.

Same flow for updates (`deploy --kind update`) and removals (`--kind remove`).

## May not
Log in to the live VPS, change risk values, deploy without a passed release review.
