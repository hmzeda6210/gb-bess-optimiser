"""Phase 2: train LightGBM quantile models, validated with TimeSeriesSplit."""

import sys
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, ".")
from src.analysis.feature_matrix import build_features

QUANTILES = [0.1, 0.5, 0.9]
FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w", "rolling_std_7d"]


#Pinball (quantile) loss for a given tau — the metric quantile models are actually scored on, not MAE
def pinball_loss(y_true, y_pred, tau):
    diff = y_true - y_pred
    return np.mean(np.maximum(tau * diff, (tau - 1) * diff))


#Train P10/P50/P90 LightGBM models per TimeSeriesSplit fold. The naive baselines are scored on the SAME test rows as the model, so the comparison is like-for-like
def train_and_evaluate(series_id: str, n_splits: int = 5):
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_pinball = {tau: [] for tau in QUANTILES}
    model_maes, naive_maes = [], []

    print(f"\n=== {series_id} ===")
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        preds = {}
        for tau in QUANTILES:
            model = lgb.LGBMRegressor(objective="quantile", alpha=tau, n_estimators=200, verbose=-1)
            model.fit(X_train, y_train)
            preds[tau] = model.predict(X_test)
            fold_pinball[tau].append(pinball_loss(y_test.values, preds[tau], tau))

        # THE KEY PART: baselines scored on the same test rows as the model.
        # lag_1d is yesterday's price for the same period (persistence),
        # lag_1w is last week's (weekly seasonal).
        err_model = np.abs(y_test.values - preds[0.5])
        err_pers = np.abs(y_test.values - X_test["lag_1d"].values)
        err_week = np.abs(y_test.values - X_test["lag_1w"].values)
        ok = ~np.isnan(err_pers) & ~np.isnan(err_week)   # rows where both baselines exist

        m, p, w = err_model[ok].mean(), err_pers[ok].mean(), err_week[ok].mean()
        model_maes.append(m)
        naive_maes.append(min(p, w))
        print(f"  Fold {fold}: P50 MAE £{m:.2f} | persistence £{p:.2f} | weekly £{w:.2f}")

    print(f"\n  Avg pinball loss per quantile:")
    for tau in QUANTILES:
        print(f"    tau={tau}: {np.mean(fold_pinball[tau]):.3f}")

    avg_m, avg_n = np.mean(model_maes), np.mean(naive_maes)
    print(f"\n  Avg P50 MAE £{avg_m:.2f} vs best naive £{avg_n:.2f} "
          f"-> {100 * (avg_n - avg_m) / avg_n:.1f}% better")


#Run the CV evaluation for both day-ahead and imbalance series
if __name__ == "__main__":
    train_and_evaluate("gb_day_ahead_price")
    train_and_evaluate("gb_imbalance_price")