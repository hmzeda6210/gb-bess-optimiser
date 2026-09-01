# Known Limitations: Phase 2 Quantile Forecasting

## P90 quantile miscalibration

The 90th-percentile (P90) quantile model is systematically miscalibrated: actual
prices exceed the P90 prediction roughly 29-31% of the time, against a target of
10%. P10 is closer to target but still slightly conservative (~5-7% vs. 10%).

**Diagnosis process:**
1. Confirmed via a calibration check (fraction of actual values falling below P10 /
   above P90 across the test set) — not visible from MAE alone.
2. Ruled out hyperparameter tuning as the cause: tuned each quantile (τ=0.1, 0.5, 0.9)
   separately via Optuna rather than sharing one parameter set. Calibration barely
   changed (day-ahead: 33% → 29% above P90; imbalance: 31% → 31%, unchanged).
3. Added a rolling 7-day price volatility feature (`rolling_std_7d`), hypothesising
   the model needed a signal for "currently volatile regime." It became the most
   important feature for day-ahead (ranked above `month`), but calibration still
   barely moved (29% → 28.7%).

**Root cause:** the feature set (settlement period, day of week, month, and price
lags/volatility) has no visibility into the discrete, largely unpredictable events
that actually drive GB price spikes — wind generation shortfalls, plant outages,
interconnector faults. Recent price volatility signals "conditions are unstable"
but not "a spike is imminent." Fixing this would require external generation/outage
data (e.g. NESO wind forecasts), which is out of scope for this phase.

**Practical implication:** any downstream use of the P90 quantile (e.g. Phase 3's
battery dispatch optimisation) should treat it as an *underestimate* of true tail
risk — the real 90th percentile is likely closer to the model's 70th percentile,
based on the ~30% miscalibration rate observed.

**Real-money illustration:** a smoke test across 6 dispatch days (see
`src/optimisation/quick_smoke_test.py`) showed the miscalibration cutting
both ways, not just one direction — e.g. 20 July: believed profit £529 vs.
actual £359 (model missed an upside spike); 15 March: believed profit £10
vs. actual £502 (model's cautious schedule coincidentally captured a spike
it hadn't planned for). Both outcomes stem from the same root cause: the
model underestimates how far prices can move, in either direction.

## MID data gap

A ~10-period gap exists in the day-ahead price series for 2025-06-26 to 2025-07-03
(327 rows instead of the expected 337 for that week). Cause not identified — could
be an Elexon-side outage or a backfill issue. This propagates into the feature
matrix: any row using a lag feature that references the missing window is dropped
rather than filled, so the effect is contained (fails safely) but not corrected.

## Seasonal weak spot

Cross-validation fold performance is uneven across seasons: the fold covering
Feb-May 2026 (spring transition) consistently shows the highest error across every
model variant tested (baseline, untuned, tuned, tuned+volatility feature). Ruled
out data gaps as the cause (fold's date range doesn't overlap the known MID gap
above). Likely explanation: spring is a genuine transition period for GB prices
(ramping solar capacity, more variable weather patterns) that is harder to predict
than settled winter or summer conditions — untested hypothesis, not confirmed.