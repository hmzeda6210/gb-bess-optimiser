"""Diagnostic: which real dates does each TimeSeriesSplit fold actually test on?"""

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from src.analysis.feature_matrix import build_features

df = build_features("gb_day_ahead_price")

tscv = TimeSeriesSplit(n_splits=5)
gap_start, gap_end = pd.Timestamp("2025-06-26", tz="UTC"), pd.Timestamp("2025-07-03", tz="UTC")

for fold, (train_idx, test_idx) in enumerate(tscv.split(df)):
    test_dates = df.iloc[test_idx]["settlement_datetime"]
    start, end = test_dates.min(), test_dates.max()
    months = sorted(test_dates.dt.month.unique())
    overlaps_gap = (start <= gap_end) and (end >= gap_start)
    print(f"Fold {fold}: {start.date()} to {end.date()}  |  months present: {months}  |  overlaps known gap: {overlaps_gap}")