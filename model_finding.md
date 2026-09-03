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

## Underestimated price level (spread compression)

A distinct failure mode from the P90 spike-miscalibration finding: on 22 July
2026, the walk-forward backtest produced a real loss of -£43.23 on a day where
perfect foresight could have made £179.86 (believed profit at forecast time
was £173.22 — the model expected a healthy profit).

Unlike the spike-miscalibration cases, every price on this day (both charge
and discharge periods) came in on the SAME side of the forecast — actual
prices were uniformly £18-38 higher than forecast, not a directional miss.
The model correctly predicted "charge cheap, discharge expensive" — it got
the direction right. The problem was scale: because the whole day's prices
shifted up together, the battery paid noticeably more to charge than
expected, and even though it also sold for more than expected, the gap
between the two shrank in real terms. Once round-trip efficiency (~85%) is
accounted for, that shrunken gap turned into a real loss instead of the
forecast profit.

Practical implication: the dispatch optimiser is vulnerable not just to
missing discrete spikes, but to systematic day-level price underestimation
eroding the efficiency margin, even when the forecasted trade direction was
correct. A pure point-forecast-driven breakeven check (as currently
implemented) doesn't account for this. A safety margin above the raw 1/eta
threshold, or a probabilistic breakeven check using the (currently
miscalibrated) P90, could help — not yet implemented, flagged for Phase 5/6.

## Sharpe ratio: corrected explanation

An earlier note in this doc incorrectly attributed the unusually high annualised
Sharpe (12.07 on the full 418-day backtest) to computing it on raw £ profit
instead of % returns. This was WRONG - Sharpe is mathematically scale-invariant
to any constant divisor (verified: Sharpe computed on £ profit and on
profit/capital_base returns are numerically identical). Converting to % returns
cannot change the ratio.

The more likely real explanation: retrain_every=30 means the same trained model
drives dispatch for 30 consecutive days at a time, making daily returns within
each retrain window correlated rather than independent. The standard sqrt(252)
annualisation formula assumes independent daily returns - when that assumption
is violated by within-window correlation, the formula overstates the true
annualised Sharpe. Not yet corrected for; flagged as a known limitation.

## Percentage-based metrics (capital base: £3,000,000 notional, ~£300k/MWh x 10MWh - assumption, not a sourced figure)

- Annualised return on capital: ~2.35-3.41% (arbitrage-only). Plausible against
  real BESS economics - arbitrage alone typically yields modest single-digit
  returns, which is why real projects stack capacity market + ancillary revenue
  alongside arbitrage. This is a sanity-check in favour of the model, not a
  standalone claim of strong performance.
- Max drawdown, as % of peak equity: roughly -0.03% - negligible relative to a
  multi-million-pound capital base, since arbitrage P&L swings are small
  relative to typical battery capex. Confirms the £1,075 max drawdown found
  earlier isn't a sign of instability, just a reflection of profit magnitudes
  being small relative to asset value.

  ## Forecast error and profit are positively correlated (confounded by volatility)

Across all 418 backtest days, daily forecast MAE (£/MWh) correlates POSITIVELY
with real profit (r=0.399) - the opposite of the naive expectation that worse
forecasts mean worse outcomes. This isn't causal: both forecast error and
profit opportunity are driven by the same underlying factor, price volatility.
Calm days are easy to forecast (low MAE) but offer little arbitrage spread (low
profit). Volatile days are hard to forecast accurately (high MAE) but offer a
much larger spread to exploit, more than compensating for the imperfect
forecast. The relationship is confounded, not causal - large forecast errors
don't cause good profit; both are symptoms of a volatile day.

## Drawdown and capture rate confirm the January weak spot from three angles

The single largest drawdown (-£1,076) and the lowest point of the 30-day
rolling capture rate (~15-20%) both occur in the same window (late Nov 2025 -
Feb 2026), independently corroborating the seasonal bar chart / heatmap finding
that January is the weakest-performing month, not spring as originally
hypothesised from the smaller Phase 2 smoke test.

## Cost sensitivity: profitability depends heavily on where costs actually land

Scenario	      Total profit	      £/MW/year	   Days profitable
No costs    	£117,114	            £20,453	      342/418 (82%)
Half costs	   £42,880	            £7,489	      235/418 (56%)
Full costs	   -£31,354	            -£5,476	      135/418 (32%)

The system is profitable at half the assumed cost level but not at the full
assumption - the headline result is genuinely sensitive to where degradation/
fee/slippage costs actually land, not robust across the plausible range. Real
degradation costs vary significantly by battery chemistry and cycle-life
warranty terms; the £9.4/MWh assumption used here is one plausible figure
within a wider published range, not a precise, sourced number. This
sensitivity should be read alongside the caveat that costs are applied
post-hoc rather than inside the optimiser's objective (see above) - a
cost-aware dispatch strategy would likely improve on all three rows shown
here by trading more selectively.