# Known Limitations and Findings

A running log of real findings, diagnosed limitations, and corrections made
during this project, organised by phase. Each finding states what was observed,
how it was diagnosed, what was ruled out, and what it means practically.

**Status of the numbers:** all backtest figures were regenerated on 8 Oct 2026
after the corrections listed at the end of this document (415 days, 5 MW / 10 MWh
battery). Two older results (forecast calibration and feature importance) were
measured before those corrections and have not been re-run; they are labelled
where they appear.

---

## Phase 2: Forecasting

### Forecast accuracy against a persistence baseline

Evaluated with expanding-window cross-validation (5 folds). The naive baseline
(persistence = yesterday's price for the same settlement period) is scored on
exactly the same rows as the model, inside each fold. Mean absolute error, £/MWh.

| Series | Model | Model MAE | Naive MAE | Result |
|---|---|---|---|---|
| Day-ahead | Untuned LightGBM P50 | £22.42 | £22.36 | -0.3% (no better than persistence) |
| Day-ahead | Optuna-tuned P50 | £20.17 | £22.36 | 9.8% better, wins all 5 folds |
| Imbalance | Untuned LightGBM P50 | £33.56 | £36.26 (best naive per fold) | 7.5% better |
| Imbalance | Optuna-tuned P50 | £31.37 | £36.49 (persistence) | 14.0% better |

**What it means:** with default settings the day-ahead forecast is level with
"just use yesterday's price". Tuning (slower learning rate, larger minimum leaf
size) produces a real improvement, but see the caveats.

**Caveats:**
- The tuned parameters were chosen by Optuna on the same data they are then
  scored on, so the tuned figures carry a mild optimistic bias. A stricter test
  would tune on an earlier period and score on a later one; not done.
- The imbalance series uses yesterday's imbalance price as a feature, which would
  not all be known at a real decision time. Treat the imbalance result as less
  reliable than the day-ahead result. Only the day-ahead model feeds the
  dispatch backtest.
- Earlier improvement figures (28% and 31%) compared the model with a baseline
  measured on a different, easier window (the last 60 days) and are withdrawn.

### Price series definition

The "day-ahead" series is Elexon's Market Index Data (MID): a volume-weighted
combination of APX and N2EX prices. It is used as a day-ahead price proxy. It has
not been verified to be the day-ahead auction price specifically, so it should be
described as the GB market index price.

Historical `published_at` timestamps are estimated as the end of the settlement
period plus a placeholder 5-minute lag, not a measured publication delay.

### P90 quantile miscalibration

*Measured before the volatility-feature fix and not re-run.*

The 90th-percentile (P90) quantile model is systematically miscalibrated: actual
prices exceed the P90 prediction roughly 29-31% of the time, against a target of
10%. P10 is closer to target but still slightly conservative (~5-7% vs. 10%).

**Diagnosis process:**
1. Confirmed via a calibration check (fraction of actual values falling below P10 /
   above P90 across the test set), not visible from MAE alone.
2. Ruled out hyperparameter tuning as the cause: tuned each quantile (τ=0.1, 0.5, 0.9)
   separately via Optuna rather than sharing one parameter set. Calibration barely
   changed (day-ahead: 33% → 29% above P90; imbalance: 31% → 31%, unchanged).
3. Added a rolling 7-day price volatility feature (`rolling_std_7d`), hypothesising
   the model needed a signal for "currently volatile regime." In that earlier run it
   ranked as the most important day-ahead feature, but calibration barely moved
   (29% → 28.7%). The feature has since been corrected so it no longer includes the
   row being predicted; feature importance and calibration have not been re-measured.

**Root cause:** the feature set (settlement period, day of week, month, and price
lags/volatility) has no visibility into the discrete, largely unpredictable events
that actually drive GB price spikes: wind generation shortfalls, plant outages,
interconnector faults. Recent price volatility signals "conditions are unstable"
but not "a spike is imminent." Fixing this would require external generation/outage
data (e.g. NESO wind forecasts), which is out of scope.

**Practical implication:** any downstream use of the P90 quantile should treat it as
an *underestimate* of true tail risk; the real 90th percentile is likely closer to
the model's 70th percentile, based on the ~30% miscalibration rate observed. Only
the P50 forecast is used by the dispatch optimiser.

**Illustration:** an earlier smoke test across 6 dispatch days (run before the
power-limit correction below) showed the miscalibration cutting both ways: on one
day the model missed an upside spike and believed profit exceeded actual profit; on
another, a cautious schedule coincidentally captured a spike it had not planned
for. Both stem from the same cause: the model underestimates how far prices can
move, in either direction. Figures not carried forward.

### MID data gap

A ~10-period gap exists in the day-ahead price series for 2025-06-26 to 2025-07-03
(327 rows instead of the expected 337 for that week). Cause not identified; could
be an Elexon-side outage or a backfill issue. This propagates into the feature
matrix: any row using a lag feature that references the missing window is dropped
rather than filled, so the effect is contained (fails safely) but not corrected.
The backtest skips any day with fewer than 46 settlement periods (27 and 29 June
2025, and the final partial day, 23 July 2026), leaving 415 test days.

### Seasonal weak spot (initial hypothesis, corrected in Phase 4)

Cross-validation fold performance is uneven across seasons: the fold covering
Feb-May 2026 (spring transition) consistently shows the highest error across every
model variant tested (baseline, untuned, tuned, tuned+volatility feature). Ruled
out data gaps as the cause (fold's date range doesn't overlap the known MID gap
above). Likely explanation at the time: spring is a genuine transition period for
GB prices (ramping solar capacity, more variable weather patterns) that is harder
to predict than settled winter or summer conditions.

**Note:** this was a hypothesis based on forecast *accuracy* (MAE), not trading
*profitability*. The full Phase 4 backtest later found a different pattern for
profitability; see "Seasonal weak spot, corrected" under Phase 4. Forecast accuracy
and financial outcome are not the same thing; this is itself one of the project's
findings.

---

## Phase 3: Optimisation

### Asset modelled

5 MW / 10 MWh battery (2-hour duration), 92.2% efficiency each way (about 85%
round trip). Charge, discharge and state of charge are in MWh per half-hour
settlement period, so the most energy that can move in one period is
5 MW × 0.5 h = 2.5 MWh. Each day starts with an empty battery and the end-of-day
state of charge is unconstrained, which is a simplification.

### Underestimated price level (spread compression)

A distinct failure mode from the P90 spike-miscalibration finding: on 22 July
2026 the walk-forward backtest produced a real loss of -£96.30 on a day where
perfect foresight could have made £149.69 (believed profit at forecast time was
£56.94, so the model expected a profit).

In the earlier version of the backtest this was traced to every price (both charge
and discharge periods) coming in on the same side of the forecast, uniformly
£18-38 higher, rather than a directional miss. That breakdown has not been repeated
on the current version, so treat it as the likely mechanism, not a re-confirmed one.
The model gets the direction right ("charge cheap, discharge expensive"); the
problem is scale. When the whole day's prices shift together, the battery pays more
to charge than expected, and even though it also sells for more, the gap between
the two shrinks in real terms. Once round-trip efficiency (~85%) is accounted for,
a shrunken gap can turn a forecast profit into a real loss.

**Practical implication:** the dispatch optimiser is vulnerable not just to
missing discrete spikes, but to systematic day-level price underestimation
eroding the efficiency margin, even when the forecasted trade direction was
correct. A pure point-forecast-driven breakeven check (as currently
implemented) doesn't account for this. A safety margin above the raw 1/eta
threshold, or a probabilistic breakeven check using a calibrated P90, could help;
not yet implemented.

---

## Phase 4: Backtesting

Walk-forward backtest, 1 June 2025 to 22 July 2026, 415 test days (retrained
every 30 days, causal: each day uses only data from before that day). Headline,
before costs: total real profit £119,666 against £234,876 under perfect foresight,
a capture rate of 50.9%. This is arbitrage on a single day-ahead price series only.

### Sharpe ratio: explanation, and why it is not quoted

The annualised Sharpe computed from daily profit is 12.56. This is not a credible
figure and is not used as a headline. An earlier note in this doc incorrectly
attributed it to computing Sharpe on raw £ profit instead of % returns. **That was
wrong:** Sharpe is mathematically scale-invariant to any constant divisor (verified
numerically), so converting to % returns cannot change the ratio.

The more likely explanation: `retrain_every=30` means the same trained model
drives dispatch for 30 consecutive days at a time, making daily returns within
each retrain window correlated rather than independent. The standard √252
annualisation assumes independent daily returns; when that is violated, the
formula overstates the true annualised Sharpe. Not corrected for.

### Percentage-based metrics

Capital base assumption: £3,000,000 notional (~£300k/MWh × 10 MWh; an assumption,
not a sourced figure).

- Annualised return on capital: ~2.4% using 252 trading days (~3.5% if annualised
  over 365 days), arbitrage-only, before costs. Plausible against real BESS
  economics: arbitrage alone typically yields modest single-digit returns, which is
  why real projects stack capacity market and ancillary revenue alongside
  arbitrage. This is a sanity check, not a claim of strong performance.
- Max drawdown: -£716, about -0.02% of the capital base. The deepest drawdown is a
  single day: 29 March 2026, which is also the worst day in the backtest. That is a
  clock-change day (46 settlement periods). It has not been investigated whether
  this loss is a genuine market move or partly an artefact of the clock-change day.
  Because the drawdown is one day, it says little about how losses accumulate over
  time.

### Forecast error and profit are positively correlated (confounded by volatility)

Across all 415 backtest days, daily forecast MAE (£/MWh) correlates **positively**
with real profit (r=0.479), the opposite of the naive expectation that worse
forecasts mean worse outcomes. This isn't causal: both forecast error and
profit opportunity are driven by the same underlying factor, price volatility.
Calm days are easy to forecast (low MAE) but offer little arbitrage spread (low
profit). Volatile days are hard to forecast accurately (high MAE) but offer a
much larger spread to exploit, more than compensating for the imperfect
forecast. The relationship is confounded, not causal.

### Seasonal weak spot, corrected: winter, not spring

The original Phase 2 hypothesis suggested spring was the weak spot, based on
forecast accuracy across cross-validation folds. The full backtest, measuring
actual trading profitability, found the opposite: **February (£123/day), January
(£144/day) and December (£177/day) are the three lowest-earning months**, while
June (£453/day), April (£419/day) and September (£384/day) are among the best.
March earns £312/day.

This was first obscured by a bug in the seasonal breakdown (grouping by month
number without year, silently merging two separate Junes/Julys, since the test
period spans 14 months, into one inflated bucket). Fixed by using profit per day,
which is independent of how many times each calendar month appears in the range.

**Root cause:** winter's flatter day-shape (no midday solar dip, established in
the exploratory analysis) offers less spread to arbitrage regardless of forecast
accuracy. January's win *rate* (77.4%) is mid-pack: the battery isn't making more
mistakes in winter, it is finding smaller opportunities (average winning day
£217.84, among the three lowest of any month alongside February £199.12 and
December £212.55). Forecast accuracy (MAE) and trading profitability are not the
same thing; this discrepancy is itself a real finding.

### Trade costs (slippage, fees, degradation)

Cost assumptions: 0.5% slippage on traded value, £2/MWh fee, £9.4/MWh degradation
(derived from a 50% cell-cost fraction of £3M capex over an 8,000-cycle rated
life). Costs are applied to the trades at actual prices, after the dispatch
schedule has been decided.

**Applying the full assumed costs to the 415-day backtest turns a profit into a
small loss:**

| Scenario | Total profit | £/MW/year (5 MW) | Days profitable |
|---|---|---|---|
| No costs | £119,666 | £21,050 | 352/415 (85%) |
| Half costs | £56,311 | £9,905 | 248/415 (60%) |
| Full costs | -£7,045 | -£1,239 | 147/415 (35%) |

"Half costs" halves all three components (slippage, fee and degradation). The
system is profitable at half the assumed cost level and roughly breaks even to
slightly loss-making at the full assumption, so the headline result is genuinely
sensitive to where degradation, fee and slippage costs actually land. Real
degradation costs vary significantly by battery chemistry and cycle-life
warranty terms; the £9.4/MWh assumption is one plausible figure within a wider
published range, not a precise, sourced number.

This is consistent with industry experience: 2-hour batteries doing arbitrage
alone frequently struggle to cover degradation and trading costs from price spread
alone, which is why real BESS projects stack multiple revenue streams (balancing
mechanism, frequency response, capacity market). This project deliberately scopes
to arbitrage-only, so this result should be read as a conservative,
single-revenue-stream figure, not a verdict on battery economics generally.

**Important caveat:** costs were applied after the fact to an already-decided
schedule, not built into the MILP's objective function. A cost-aware optimiser
would make fewer, more selective trades, only acting on spreads wide enough to
clear the true breakeven (efficiency + degradation + fees combined) rather than the
efficiency-only threshold currently used. The figures above are therefore likely a
pessimistic lower bound, not the system's true achievable performance under
proper cost-aware dispatch. Building a cost-aware objective is the natural next
step, not yet implemented.

---

## Corrections made (8 Oct 2026)

An accuracy audit before publishing the results found and fixed the following.

1. **Power limit units.** The dispatch model treated the 5 MW limit as 5 MWh per
   half-hour, i.e. an effective 10 MW battery, while £/MW/year divided by 5 MW. Now
   the per-period limit is 5 MW × 0.5 h = 2.5 MWh. Effect: perfect-foresight profit
   fell by about 10%.
2. **Volatility feature leak.** `rolling_std_7d` included the row being predicted.
   It now uses data from at least one day earlier (checked against a hand
   calculation). Effect on forecast accuracy was negligible (day-ahead untuned
   MAE £22.73 → £22.42).
3. **Baseline mismatch.** Model and baseline MAE were measured on different
   windows. Both are now scored on identical rows; the earlier 28% / 31%
   improvement claims are withdrawn.
4. **Cost pricing.** Slippage is now charged on actual prices (not forecast
   prices) and on the absolute price (negative prices no longer create a credit).
   The headline "after costs" figure now means the full cost assumptions.
5. **Partial days.** Days with fewer than 46 periods are skipped (415 test days).
6. **Model settings.** The P50 parameters were re-tuned on the corrected feature.

Headline change: total profit £117,114 → £119,666; capture rate 44.6% → 50.9%;
£/MW/year (before costs) £20,453 → £21,050; max drawdown -£1,076 → -£716.