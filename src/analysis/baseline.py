"""Phase 1 naive baseline: persistence vs weekly-seasonal, evaluated on a holdout period."""

import sqlite3
import pandas as pd
import numpy as np

#Load one price series from gb_prices.db by series_id (e.g. 'gb_day_ahead_price', 'gb_imbalance_price'), sorted by time.
def load_series(series_id: str) -> pd.DataFrame:
    conn = sqlite3.connect("gb_prices.db")
    df = pd.read_sql_query(
        "SELECT settlement_datetime, settlement_period, value "
        "FROM price_series WHERE series_id = ? ORDER BY settlement_datetime",
        conn, params=(series_id,)
    )
    df["settlement_datetime"] = pd.to_datetime(df["settlement_datetime"])
    conn.close()
    return df.reset_index(drop=True)

#Baseline check: compare persistence (yesterday) vs weekly-seasonal (last week) naive forecasts on a holdout, the MAE a real model must beat
def evaluate_naive_baselines(df: pd.DataFrame, test_days: int = 60):
    """
    Shifts assume ~48 periods/day (a small, known imprecision on the rare
    clock-change day — negligible across hundreds of test periods).
    """
    df = df.copy()
    df["persistence_pred"] = df["value"].shift(48)      # same period, 1 day ago
    df["weekly_pred"] = df["value"].shift(48 * 7)        # same period, 1 week ago

    test_periods = test_days * 48
    test = df.iloc[-test_periods:].dropna(subset=["persistence_pred", "weekly_pred"])

    persistence_mae = np.mean(np.abs(test["value"] - test["persistence_pred"]))
    weekly_mae = np.mean(np.abs(test["value"] - test["weekly_pred"]))

    print(f"  Test window: last {test_days} days ({len(test)} settlement periods)")
    print(f"  Persistence (yesterday, same period)  MAE: £{persistence_mae:.2f}")
    print(f"  Weekly (last week, same period+day)   MAE: £{weekly_mae:.2f}")

    winner = "Persistence" if persistence_mae < weekly_mae else "Weekly"
    print(f"  --> Best naive baseline: {winner}\n")

#Run the baseline check for both day-ahead and imbalance price series.
if __name__ == "__main__":
    print("Day-ahead price baseline:")
    evaluate_naive_baselines(load_series("gb_day_ahead_price"))

    print("Imbalance price baseline:")
    evaluate_naive_baselines(load_series("gb_imbalance_price"))
    
"""Phase 1 naive baseline: persistence vs weekly-seasonal, evaluated on a holdout period.

Result (2025-05-01 to 2026-07-23 data, last 60 days holdout):
    Day-ahead: persistence wins, MAE £28.52
    Imbalance: weekly wins (barely), MAE £45.51
these are the numbers LightGBM models need to beat.
"""