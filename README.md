# gb-bess-optimiser

A GB battery dispatch system: day-ahead and imbalance price forecasting (quantile
regression), MILP-based battery scheduling, and backtesting against a
perfect-foresight benchmark.

**Live dashboard:** [hamza6210.pythonanywhere.com](https://hamza6210.pythonanywhere.com)

## Data pipeline

Pulls half-hourly GB electricity prices from Elexon's public BMRS API:
- Day-ahead reference prices (Market Index Data)
- Imbalance/system prices (settlement)

Prices are timestamped both by the settlement period they describe and by
when they became knowable, to keep forecasting features free of lookahead bias.

~14 months of historical data (May 2025 – July 2026) backfilled for both series.

## Exploratory analysis

- `src/analysis/explore.py` — seasonal price shape comparison, price distribution analysis
- `src/analysis/baseline.py` — naive forecasting baselines (persistence, weekly-seasonal)

## Forecasting

Quantile regression (LightGBM, τ = 0.1/0.5/0.9) for both price series, validated
with expanding-window `TimeSeriesSplit` and tuned with Optuna.

- `src/analysis/feature_matrix.py` — leakage-safe, gap-safe feature engineering
  (timestamp-based lags, calendar features, rolling volatility)
- `src/forecasting/train_quantile.py` — model training and cross-validated evaluation
- `src/forecasting/tune_and_train.py` — Optuna hyperparameter search per quantile
- `src/forecasting/evaluate_plots.py` — calibration, prediction bands, feature importance

**Results (P50, vs. naive baseline MAE):**

| Series | Naive baseline | Tuned model |
|---|---|---|
| Day-ahead | £28.52 | £20.64 |
| Imbalance | £45.51 | £31.31 |

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

A custom `WalkForwardBacktester` (causal, periodically-retrained) replays the
full forecast → dispatch → realised-price pipeline across every day in the
dataset.

- `src/backtesting/walk_forward.py` — the backtest loop and result caching
- `src/backtesting/metrics.py` — capture rate, Sharpe, drawdown (£ and %),
  £/MW/year, seasonal breakdown
- `src/backtesting/costs.py` — trade cost modeling (slippage, fees, degradation)
- `src/backtesting/plot_seasonal.py` — equity curve, rolling capture rate,
  seasonal heatmap, forecast-error correlation, and a combined tearsheet

**Results (418 days, 2025-06-01 to 2026-07-23):**

| Metric | Before costs | After costs (assumption-dependent) |
|---|---|---|
| Total profit | £117,114 | -£31,354 to £42,880 (see sensitivity analysis) |
| Capture rate | 44.6% of perfect foresight | — |
| £/MW/year | £20,453 | -£5,476 to £7,489 |

Arbitrage-only trading frequently fails to cover realistic degradation and
transaction costs at this battery duration — consistent with why real BESS
projects stack multiple revenue streams rather than relying on day-ahead
arbitrage alone.

See [`model_finding.md`](model_finding.md) for the full findings log,
including the P90 miscalibration diagnosis, the corrected seasonal finding,
and the cost sensitivity analysis.

## Dashboard

An interactive Dash application, deployed live (link above).

- **Overview** — pick any backfilled date, see the real MILP dispatch schedule
  and price chart, click any period for a "why this decision" panel (binding
  constraint, SoC, spread vs. last charge — all derived live from the
  schedule, nothing fabricated)
- **Performance** — live equity curve (before/after trade costs), seasonality,
  year-over-year comparison, cost sensitivity, and the full findings log

Dispatch results are precomputed (`scripts/precompute_dispatch.py`) for fast
lookups rather than solving the MILP live on every request.

## Production deployment

- `src/deployment/run_daily.py` — computes dates relative to actual runtime
  (not hardcoded), UK-timezone-aware, with an ingestion retry/cutoff pattern
  and a runtime leakage assertion. Verified locally and via Docker
  (environment parity confirmed — identical output bare vs. containerised).
- `Dockerfile` — containerised pipeline, tested locally.

Live scheduled cloud deployment (Cloud Run + Cloud Scheduler) was scoped and
the container verified, but not completed — see `model_finding.md` for why.

## Setup

```bash
pip install -r requirements.txt
python -m src.ingestion.run_backfill mid 2025-05-01 2026-07-23
python -m src.ingestion.run_backfill disebsp 2025-05-01 2026-07-23
python -m src.forecasting.train_quantile
python -m src.backtesting.walk_forward
python -m src.backtesting.plot_seasonal
python -m dashboard.app
```