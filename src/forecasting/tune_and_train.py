"""Phase 2: Optuna hyperparameter tuning, then final quantile model training."""

import numpy as np
import lightgbm as lgb
import optuna
from sklearn.model_selection import TimeSeriesSplit

from src.analysis.feature_matrix import build_features

optuna.logging.set_verbosity(optuna.logging.WARNING)

QUANTILES = [0.1, 0.5, 0.9]
FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w"]

BASELINE_MAE = {
    "gb_day_ahead_price": 28.52,
    "gb_imbalance_price": 45.51,
}


def pinball_loss(y_true, y_pred, tau):
    diff = y_true - y_pred
    return np.mean(np.maximum(tau * diff, (tau - 1) * diff))


def tune_hyperparameters(X, y, n_trials: int = 30) -> dict:
    """Tunes once using the median (tau=0.5) as the search objective; the
    resulting hyperparameters are then reused for all three quantiles."""

    def objective(trial):
        params = {
            "objective": "quantile",
            "alpha": 0.5,
            "verbose": -1,
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        }
        tscv = TimeSeriesSplit(n_splits=3)  # fewer folds during search, for speed
        losses = []
        for train_idx, test_idx in tscv.split(X):
            model = lgb.LGBMRegressor(**params)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[test_idx])
            losses.append(pinball_loss(y.iloc[test_idx].values, pred, 0.5))
        return np.mean(losses)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    print(f"  Best trial pinball loss (tau=0.5): {study.best_value:.3f}")
    print(f"  Best params: {study.best_params}")
    return study.best_params


def evaluate_tuned(series_id: str, best_params: dict, n_splits: int = 5):
    """Re-runs the full 5-fold evaluation using the tuned hyperparameters,
    same structure as the earlier untuned run, for a fair comparison."""
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_p50_mae = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = lgb.LGBMRegressor(objective="quantile", alpha=0.5, verbose=-1, **best_params)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        p50_mae = np.mean(np.abs(y_test.values - pred))
        fold_p50_mae.append(p50_mae)
        print(f"  Fold {fold}: P50 MAE=£{p50_mae:.2f}")

    avg_mae = np.mean(fold_p50_mae)
    baseline = BASELINE_MAE[series_id]
    print(f"  Avg tuned P50 MAE: £{avg_mae:.2f}  vs  naive baseline £{baseline:.2f}")
    return avg_mae


if __name__ == "__main__":
    for series_id in ["gb_day_ahead_price", "gb_imbalance_price"]:
        print(f"\n=== {series_id}: tuning ===")
        df = build_features(series_id)
        X, y = df[FEATURE_COLS], df["y"]
        best_params = tune_hyperparameters(X, y, n_trials=30)

        print(f"\n=== {series_id}: evaluating tuned model ===")
        evaluate_tuned(series_id, best_params)