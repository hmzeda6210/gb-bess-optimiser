"""Phase 2: build leakage-safe feature matrices from stored price series."""

import sqlite3
import pandas as pd

#Load one price series from gb_prices.db by series_id, sorted by time
def load_series(series_id: str) -> pd.DataFrame:
    conn = sqlite3.connect("gb_prices.db")
    df = pd.read_sql_query(
        "SELECT settlement_datetime, settlement_period, value "
        "FROM price_series WHERE series_id = ? ORDER BY settlement_datetime",
        conn, params=(series_id,)
    )
    df["settlement_datetime"] = pd.to_datetime(df["settlement_datetime"])
    conn.close()
    return df

#Add a lagged value column by joining on actual settlement_datetime (not row shift), so gaps/clock changes don't silently misalign like row-position shifting would
def add_timestamp_lag(df: pd.DataFrame, days_back: int, col_name: str) -> pd.DataFrame:
    """Gap-safe lag: join on actual timestamp, not row position."""
    lagged = df[["settlement_datetime", "value"]].copy()
    lagged["settlement_datetime"] = lagged["settlement_datetime"] + pd.Timedelta(days=days_back)
    lagged = lagged.rename(columns={"value": col_name})
    return df.merge(lagged, on="settlement_datetime", how="left")

#Build the leakage-safe model-ready feature matrix (lag_1d, lag_1w, rolling_std_7d, day/month) for one series, dropping rows with incomplete lag history
def build_features(series_id: str) -> pd.DataFrame:
    df = load_series(series_id)
    df["y"] = df["value"]
    df = add_timestamp_lag(df, days_back=1, col_name="lag_1d")
    df = add_timestamp_lag(df, days_back=7, col_name="lag_1w")
    df["day_of_week"] = df["settlement_datetime"].dt.dayofweek
    df["month"] = df["settlement_datetime"].dt.month
    df["rolling_std_7d"] = df["value"].rolling(window=336, min_periods=48).std()

    before = len(df)
    df = df.dropna(subset=["lag_1d", "lag_1w", "rolling_std_7d"]).reset_index(drop=True)
    print(f"{series_id}: dropped {before - len(df)} rows with missing lag features")

    return df[["settlement_datetime", "settlement_period", "day_of_week", "month",
               "lag_1d", "lag_1w", "rolling_std_7d", "y"]]

#Build feature matrices for both series and print their shapes/head for a sanity check
if __name__ == "__main__":
    day_ahead_features = build_features("gb_day_ahead_price")
    imbalance_features = build_features("gb_imbalance_price")

    print(f"\nDay-ahead feature matrix: {day_ahead_features.shape}")
    print(day_ahead_features.head())
    print(f"\nImbalance feature matrix: {imbalance_features.shape}")
    print(imbalance_features.head())