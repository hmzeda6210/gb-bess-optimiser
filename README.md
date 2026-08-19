# gb-bess-optimiser

A GB battery dispatch system: day-ahead and imbalance price forecasting (quantile
regression), MILP-based battery scheduling, and backtesting against a
perfect-foresight benchmark.

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

See [`docs/model_limitations.md`](docs/model_limitations.md) for known issues,
including P90 quantile miscalibration and the diagnostic process behind it.

## Setup

```bash
pip install -r requirements.txt
python -m src.ingestion.run_backfill mid 2025-05-01 2026-07-23
python -m src.ingestion.run_backfill disebsp 2025-05-01 2026-07-23
python -m src.forecasting.train_quantile
```