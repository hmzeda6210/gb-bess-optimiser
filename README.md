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

`src/analysis/explore.py` — seasonal price shape comparison, price distribution analysis
`src/analysis/baseline.py` — naive forecasting baselines (persistence, weekly-seasonal)

## Setup

```bash
pip install -r requirements.txt
python -m src.ingestion.run_backfill mid 2025-05-01 2026-07-23
python -m src.ingestion.run_backfill disebsp 2025-05-01 2026-07-23
```