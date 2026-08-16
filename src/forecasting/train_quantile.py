"""Phase 2: train LightGBM quantile models, validated with TimeSeriesSplit."""

import sys
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, ".")
from src.analysis.feature_matrix import build_features

QUANTILES = [0.1, 0.5, 0.9]
FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w"]

BASELINE_MAE = {
    "gb_day_ahead_price": 28.52,
    "gb_imbalance_price": 45.51,
}


def pinball_loss(y_true, y_pred, tau):
    diff = y_true - y_pred
    return np.mean(np.maximum(tau * diff, (tau - 1) * diff))


def train_and_evaluate(series_id: str, n_splits: int = 5):
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_pinball = {tau: [] for tau in QUANTILES}
    fold_p50_mae = []

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

        p50_mae = np.mean(np.abs(y_test.values - preds[0.5]))
        fold_p50_mae.append(p50_mae)
        print(f"  Fold {fold}: train={len(train_idx)}, test={len(test_idx)}, P50 MAE=£{p50_mae:.2f}")

    print(f"\n  Avg pinball loss per quantile:")
    for tau in QUANTILES:
        print(f"    tau={tau}: {np.mean(fold_pinball[tau]):.3f}")

    avg_p50_mae = np.mean(fold_p50_mae)
    baseline = BASELINE_MAE[series_id]
    verdict = "BEATS baseline" if avg_p50_mae < baseline else "does NOT beat baseline"
    print(f"\n  Avg P50 MAE: £{avg_p50_mae:.2f}  vs  baseline £{baseline:.2f}  -->  {verdict}")


if __name__ == "__main__":
    train_and_evaluate("gb_day_ahead_price")
    train_and_evaluate("gb_imbalance_price")