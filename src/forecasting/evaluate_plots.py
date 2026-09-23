"""Phase 2: visual evaluation — calibration, actual-vs-predicted band, feature importance."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

from src.analysis.feature_matrix import build_features

QUANTILES = [0.1, 0.5, 0.9]
FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w", "rolling_std_7d"]

#Fit one LightGBM model per quantile using already-tuned hyperparameters (from tune_and_train.py)
def train_final_models(X_train, y_train, params_by_quantile: dict):
    models = {}
    for tau in QUANTILES:
        m = lgb.LGBMRegressor(objective="quantile", alpha=tau, verbose=-1, **params_by_quantile[tau])
        m.fit(X_train, y_train)
        models[tau] = m
    return models

#Check whether the P10-P90 band actually contains ~80% of actuals — a bar chart of below/within/above fractions vs their targets
def plot_calibration(y_test, preds: dict, series_id: str):
    below_p10 = np.mean(y_test < preds[0.1])
    above_p90 = np.mean(y_test > preds[0.9])
    within_band = np.mean((y_test >= preds[0.1]) & (y_test <= preds[0.9]))

    print(f"\n{series_id} calibration:")
    print(f"  Actual below P10 prediction: {below_p10:.1%}  (target: ~10%)")
    print(f"  Actual above P90 prediction: {above_p90:.1%}  (target: ~10%)")
    print(f"  Actual within P10-P90 band:  {within_band:.1%}  (target: ~80%)")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Below P10", "Within band", "Above P90"],
           [below_p10, within_band, above_p90], color=["#d62728", "#2ca02c", "#d62728"])
    ax.axhline(0.10, color="gray", linestyle="--", linewidth=1, label="target: 10%")
    ax.set_ylabel("Fraction of actual values")
    ax.set_title(f"{series_id}: quantile calibration")
    ax.legend()
    fig.savefig(f"calibration_{series_id}.png")
    print(f"  Saved calibration_{series_id}.png")

#Plots the last n_periods (default: 1 week) of the test set
def plot_band_over_time(df_test: pd.DataFrame, preds: dict, series_id: str, n_periods: int = 336):
    """Plots the last n_periods (default: 1 week) of the test set."""
    plot_df = df_test.tail(n_periods).copy()
    idx = plot_df.index

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(plot_df["settlement_datetime"], preds[0.1][idx], preds[0.9][idx],
                     alpha=0.2, color="tab:blue", label="P10-P90 band")
    ax.plot(plot_df["settlement_datetime"], preds[0.5][idx], color="tab:blue", label="P50 prediction")
    ax.plot(plot_df["settlement_datetime"], plot_df["y"], color="black", linewidth=1, label="Actual")
    ax.set_ylabel("£/MWh")
    ax.set_title(f"{series_id}: actual vs predicted, last week of test set")
    ax.legend()
    fig.savefig(f"band_{series_id}.png")
    print(f"  Saved band_{series_id}.png")

#Plot LightGBM feature importances from the P50 model as a proxy for all three quantiles
def plot_feature_importance(models: dict, series_id: str):
    model = models[0.5]  # use the median model as representative
    importances = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values()

    fig, ax = plt.subplots(figsize=(6, 4))
    importances.plot.barh(ax=ax)
    ax.set_title(f"{series_id}: feature importance (P50 model)")
    fig.tight_layout()
    fig.savefig(f"importance_{series_id}.png")
    print(f"  Saved importance_{series_id}.png")

#Full evaluation pipeline for one series: train on the last CV fold, then generate calibration, band, and importance plots
def run(series_id: str, params_by_quantile: dict):
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=5)
    train_idx, test_idx = list(tscv.split(X))[-1]

    models = train_final_models(X.iloc[train_idx], y.iloc[train_idx], params_by_quantile)
    preds = {tau: models[tau].predict(X.iloc[test_idx]) for tau in QUANTILES}
    y_test = y.iloc[test_idx].values

    plot_calibration(y_test, preds, series_id)
    plot_band_over_time(df.iloc[test_idx].reset_index(drop=True),
                         {tau: pd.Series(p) for tau, p in preds.items()}, series_id)
    plot_feature_importance(models, series_id)

#Hardcoded best hyperparameters (from Optuna tuning) per series/quantile, then run the full plot pipeline for both series
if __name__ == "__main__":
    day_ahead_params = {
        0.1: {"num_leaves": 15, "learning_rate": 0.030953, "n_estimators": 105, "min_child_samples": 5},
        0.5: {"num_leaves": 19, "learning_rate": 0.017032, "n_estimators": 263, "min_child_samples": 33},
        0.9: {"num_leaves": 16, "learning_rate": 0.032069, "n_estimators": 50, "min_child_samples": 50},
    }
    imbalance_params = {
        0.1: {"num_leaves": 15, "learning_rate": 0.095773, "n_estimators": 64, "min_child_samples": 16},
        0.5: {"num_leaves": 15, "learning_rate": 0.020373, "n_estimators": 89, "min_child_samples": 5},
        0.9: {"num_leaves": 19, "learning_rate": 0.012206, "n_estimators": 176, "min_child_samples": 23},
    }

    run("gb_day_ahead_price", day_ahead_params)
    run("gb_imbalance_price", imbalance_params)