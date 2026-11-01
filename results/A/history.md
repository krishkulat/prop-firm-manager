# Strategy A — history

- 2026-11-01 — Setup diagnostics on real XAUUSD M15 data (2019-01 → 2025-10 research split), run by hand outside
  the worker while checking the data export. **Count these as 2 trials of H-001.**
  - v1.0 defaults (range filter 0.5–2.0× H1 ATR): 58 signals in ~7 years; backtest halted at the 6% kill switch
    in 2020 after 17 trades. Diagnosis: the 05:30–12:30 IST range is 1.8–3.9× H1 ATR on 80% of days (median 2.67×),
    so the filter kept only 18% of days. Design error in the seed parameters, not a market finding.
  - Range filter 1.5–4.0×: 451 signals; still halted by the kill switch in 2019 after 21 trades (PF 0.14).
    Diagnosis: research backtests must not use the challenge kill switch. Fixed in the worker (research mode:
    no kill, no throttle; the kill switch is tested in propsim).
  - Cost note: average stop ≈ $2.33 vs ≈ $0.67 round-trip cost (spread + 0.30 slippage per side) → costs ≈ 29% of
    1R. Tight-stop variants are structurally disadvantaged under our conservative cost model.
- 2026-11-01 — v1.1: range filter defaults 1.5/4.0, sweep ranges rescaled. Baseline job J-20261101-001 updated to
  v1.1 defaults; it will be the first full-period research backtest.
