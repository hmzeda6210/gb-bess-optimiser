# gb-bess-optimiser

A GB battery dispatch system: day-ahead and imbalance price forecasting (quantile
regression), MILP-based battery scheduling, and backtesting against a
perfect-foresight benchmark.

**Live dashboard:** [hamza6210.pythonanywhere.com](https://hamza6210.pythonanywhere.com)
(hosted on a free PythonAnywhere account, so it may occasionally be offline)

**Asset modelled:** 5 MW / 10 MWh battery (2-hour), 92.2% efficiency each way
(about 85% round trip). Arbitrage on one price series only, no ancillary revenue.

## Data pipeline

Pulls half-hourly GB electricity prices from Elexon's public BMRS API:
- Market Index Data (volume-weighted APX and N2EX prices), used as the day-ahead
  price proxy
- Imbalance/system prices (settlement)

Every price is stored with both the settlement period it describes and a
`published_at` timestamp for when it became knowable. For historical data,
`published_at` is estimated (period end plus an assumed 5-minute lag), not
measured. Features are built from timestamp-based lags so each row only sees
earlier data.

~14 months of historical data (May 2025 – July 2026) backfilled for both series.

## Exploratory analysis

- `src/analysis/explore.py` — seasonal price shape comparison, price distribution analysis
- `src/analysis/baseline.py` — naive forecasting baselines (persistence, weekly-seasonal)

## Forecasting

Quantile regression (LightGBM, τ = 0.1/0.5/0.9) for both price series, validated
with expanding-window `TimeSeriesSplit` and tuned with Optuna. Only the P50
forecast feeds the optimiser.

- `src/analysis/feature_matrix.py` — gap-safe feature engineering (timestamp-based
  lags, calendar features, rolling volatility lagged by one day)
- `src/forecasting/train_quantile.py` — model training and cross-validated evaluation
- `src/forecasting/tune_and_train.py` — Optuna hyperparameter search (seeded)
- `src/forecasting/evaluate_plots.py` — calibration, prediction bands, feature importance

**Results (P50 mean absolute error, 5-fold expanding-window CV, persistence baseline
scored on the same rows):**

| Series | Persistence | Tuned model | Improvement |
|---|---|---|---|
| Day-ahead | £22.36 | £20.17 | 9.8% |
| Imbalance | £36.49 | £31.37 | 14.0% |

With default (untuned) settings the day-ahead model is level with persistence
(-0.3%); the improvement comes from tuning. Tuning used the same data it is scored
on, so these figures are mildly optimistic. See `model_finding.md`.

## Optimisation

Battery dispatch formulated as a Mixed-Integer Linear Program (Pyomo + HiGHS),
with a binary variable per period enforcing charge/discharge exclusivity and
correct handling of negative price periods.

- `src/optimisation/toy_milp.py` — 3-period reference case, verified against a
  hand-calculated optimum (£120 profit) before scaling up
- `src/optimisation/dispatch.py` — reusable 48-period dispatch model with
  physical sanity checks (SoC bounds, power limits, no simultaneous charge/discharge)
- `src/optimisation/forecast_dispatch.py` — dispatch driven by the Phase 2
  forecast, then re-priced against actual outcomes (forecast-driven vs.
  perfect-foresight profit)

## Backtesting

A custom `WalkForwardBacktester` (causal, retrained every 30 days) replays the
full forecast → dispatch → realised-price pipeline across every day in the
dataset.

- `src/backtesting/walk_forward.py` — the backtest loop and result caching
- `src/backtesting/metrics.py` — capture rate, drawdown (£ and %), £/MW/year,
  seasonal breakdown
- `src/backtesting/costs.py` — trade cost modeling (slippage, fees, degradation)
- `src/backtesting/plot_seasonal.py` — equity curve, rolling capture rate,
  seasonal heatmap, forecast-error correlation, and a combined tearsheet

**Results (415 days, 2025-06-01 to 2026-07-22):**

| Metric | Before costs | With assumed costs |
|---|---|---|
| Total profit | £119,666 | -£7,045 (full) to £56,311 (half) |
| Capture rate | 50.9% of perfect foresight | — |
| £/MW/year (5 MW) | £21,050 | -£1,239 to £9,905 |

Full costs are 0.5% slippage, £2/MWh fee and £9.4/MWh degradation; half costs
halve all three. Costs are applied after the schedule is decided, not built into
the optimiser, and they are assumptions, not measured values.

Arbitrage-only trading on a 2-hour battery struggles to cover realistic
degradation and transaction costs, which is consistent with why real BESS
projects stack multiple revenue streams rather than relying on day-ahead
arbitrage alone.

See [`model_finding.md`](model_finding.md) for the full findings log,
including the P90 miscalibration diagnosis, the seasonal finding, the cost
sensitivity analysis and the corrections made during an accuracy audit.

## Key limitations

- Day-ahead price proxy only: no balancing, ancillary or capacity revenue.
- Costs are post-hoc assumptions; a cost-aware optimiser would trade less.
- Each day starts with an empty battery and the end state is unconstrained.
- Tuned model settings were selected on the same data they are scored on.
- The P90 forecast is miscalibrated (actual prices exceed it about 30% of the time).
- The Sharpe ratio from this backtest is overstated and is not quoted.

## Dashboard

An interactive Dash application, deployed live (link above).

- **Overview** — pick any backfilled date and see the MILP dispatch schedule
  the optimiser would choose with perfect knowledge of that day's prices, plus the
  price chart. Click any period for a "why this decision" panel (binding
  constraint, SoC, spread vs. last charge), all derived from the schedule.
- **Performance** — equity curve (before costs, and with full assumed costs),
  seasonality, year-over-year comparison, cost sensitivity, and the findings log.

Dispatch results are precomputed (`scripts/precompute_dispatch.py`) for fast
lookups rather than solving the MILP live on every request.

## Production deployment

- `src/deployment/run_daily.py` — computes dates relative to actual runtime
  (not hardcoded), UK-timezone-aware, with an ingestion retry/cutoff pattern
  and a runtime leakage assertion. Verified locally and via Docker
  (environment parity confirmed, identical output bare vs. containerised).
- `Dockerfile` — containerised pipeline, tested locally.

Live scheduled cloud deployment (Cloud Run + Cloud Scheduler) was scoped and
the container verified, but not completed.

## Setup

```bash
pip install -r requirements.txt
python -m src.ingestion.run_backfill mid 2025-05-01 2026-07-23
python -m src.ingestion.run_backfill disebsp 2025-05-01 2026-07-23
python -m src.forecasting.train_quantile
python -m src.forecasting.tune_and_train
python -m src.backtesting.walk_forward
python scripts/precompute_dispatch.py
python -m src.backtesting.plot_seasonal
python -m dashboard.app
```