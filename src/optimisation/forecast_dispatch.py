"""Phase 3: dispatch driven by the Phase 2 P50 forecast, then re-priced
against actual outcomes — the honest, forecast-driven version of the MILP,
as opposed to the perfect-foresight version tested earlier."""

import pandas as pd
import lightgbm as lgb

from src.analysis.feature_matrix import build_features
from src.optimisation.dispatch import run_dispatch, check_schedule, load_day_ahead_prices

FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w", "rolling_std_7d"]

P50_PARAMS = {"num_leaves": 19, "learning_rate": 0.017032, "n_estimators": 263, "min_child_samples": 33}



"""Trains on everything strictly BEFORE target_date, forecasts that one
    day's 48 periods. This mirrors a real decision: on the morning of
    target_date - 1, you only know the past."""
def forecast_day_ahead_p50(target_date: str) -> dict:
    df = build_features("gb_day_ahead_price")
    target_ts = pd.Timestamp(target_date, tz="UTC")

    train_mask = df["settlement_datetime"] < target_ts
    test_mask = df["settlement_datetime"].dt.date == target_ts.date()

    X_train, y_train = df.loc[train_mask, FEATURE_COLS], df.loc[train_mask, "y"]
    X_test = df.loc[test_mask, FEATURE_COLS]
    test_periods = df.loc[test_mask, "settlement_period"].astype(int).tolist()

    model = lgb.LGBMRegressor(objective="quantile", alpha=0.5, verbose=-1, **P50_PARAMS)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    return dict(zip(test_periods, preds))

#Dispatch using the forecast, then re-price that same schedule against actual prices — measures the profit gap forecast error causes."""
def evaluate_forecast_driven_dispatch(target_date: str, capacity: float, max_power: float,
                                       eta_c: float, eta_d: float):
    forecast_prices = forecast_day_ahead_p50(target_date)
    actual_prices = load_day_ahead_prices(target_date)

    # decide the schedule using the FORECAST
    believed_profit, schedule = run_dispatch(forecast_prices, capacity, max_power, eta_c, eta_d)

    # re-price that SAME schedule against what actually happened
    real_profit = sum(
        actual_prices[r["period"]] * (r["discharge"] - r["charge"])
        for r in schedule if r["period"] in actual_prices
    )

    checks = check_schedule(schedule, capacity, max_power, eta_c, eta_d)

    return {
        "believed_profit": believed_profit,
        "real_profit": real_profit,
        "gap": believed_profit - real_profit,
        "schedule": schedule,
        "checks": checks,
    }
    
'''Trains once on everything strictly before cutoff_date. 
Pass in an already-loaded feature matrix (from build_features) rather than reloading it every call
the raw data doesn't change day to day, only the training cutoff does'''
def train_p50_model(df: pd.DataFrame, cutoff_date: str):
    cutoff_ts = pd.Timestamp(cutoff_date, tz="UTC")
    train_mask = df["settlement_datetime"] < cutoff_ts
    X_train, y_train = df.loc[train_mask, FEATURE_COLS], df.loc[train_mask, "y"]
    model = lgb.LGBMRegressor(objective="quantile", alpha=0.5, verbose=-1, **P50_PARAMS)
    model.fit(X_train, y_train)
    return model

#Forecasts one day using an ALREADY-TRAINED model - no retraining here
def forecast_with_model(df: pd.DataFrame, model, target_date: str) -> dict:
    target_ts = pd.Timestamp(target_date, tz="UTC")
    test_mask = df["settlement_datetime"].dt.date == target_ts.date()
    X_test = df.loc[test_mask, FEATURE_COLS]
    periods = df.loc[test_mask, "settlement_period"].astype(int).tolist()
    preds = model.predict(X_test)
    return dict(zip(periods, preds))


if __name__ == "__main__":
    result = evaluate_forecast_driven_dispatch(
        "2026-07-20", capacity=10.0, max_power=5.0, eta_c=0.922, eta_d=0.922
    )

    print(f"Believed profit (decided using forecast): £{result['believed_profit']:.2f}")
    print(f"Real profit (same schedule, actual prices): £{result['real_profit']:.2f}")
    print(f"Gap: £{result['gap']:.2f}")
    print(f"Checks clean: {result['checks']['all_clean']}")