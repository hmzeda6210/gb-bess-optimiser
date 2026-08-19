"""Phase 2: Optuna hyperparameter tuning, then final quantile model training."""

import numpy as np
import lightgbm as lgb
import optuna
from sklearn.model_selection import TimeSeriesSplit

from src.analysis.feature_matrix import build_features

optuna.logging.set_verbosity(optuna.logging.WARNING)

FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w", "rolling_std_7d"]

BASELINE_MAE = {
    "gb_day_ahead_price": 28.52,
    "gb_imbalance_price": 45.51,
}


def pinball_loss(y_true, y_pred, tau):
    diff = y_true - y_pred
    return np.mean(np.maximum(tau * diff, (tau - 1) * diff))


def tune_hyperparameters(X, y, alpha: float, n_trials: int = 30) -> dict:
    """Tunes for a SPECIFIC quantile (alpha) — both the model and the scoring
    metric use the same alpha, so they can never silently mismatch."""

    def objective(trial):
        params = {
            "objective": "quantile",
            "alpha": alpha,
            "verbose": -1,
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        }
        tscv = TimeSeriesSplit(n_splits=3)
        losses = []
        for train_idx, test_idx in tscv.split(X):
            model = lgb.LGBMRegressor(**params)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[test_idx])
            losses.append(pinball_loss(y.iloc[test_idx].values, pred, alpha))  # <-- matches now
        return np.mean(losses)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    print(f"  Best trial pinball loss (tau={alpha}): {study.best_value:.3f}")
    print(f"  Best params: {study.best_params}")
    return study.best_params


def evaluate_tuned(series_id: str, best_params: dict, alpha: float, n_splits: int = 5):
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_mae = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = lgb.LGBMRegressor(objective="quantile", alpha=alpha, verbose=-1, **best_params)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mae = np.mean(np.abs(y_test.values - pred))
        fold_mae.append(mae)
        print(f"  Fold {fold}: tau={alpha} MAE=£{mae:.2f}")

    avg_mae = np.mean(fold_mae)
    print(f"  Avg tuned tau={alpha} MAE: £{avg_mae:.2f}")
    if alpha == 0.5:
        print(f"  (compare vs naive baseline £{BASELINE_MAE[series_id]:.2f})")
    return avg_mae


if __name__ == "__main__":
    ALPHA_TO_TUNE = 0.9  # change this to 0.1, 0.5, or 0.9 as needed

    for series_id in ["gb_day_ahead_price", "gb_imbalance_price"]:
        print(f"\n=== {series_id}: tuning tau={ALPHA_TO_TUNE} ===")
        df = build_features(series_id)
        X, y = df[FEATURE_COLS], df["y"]
        best_params = tune_hyperparameters(X, y, alpha=ALPHA_TO_TUNE, n_trials=30)

        print(f"\n=== {series_id}: evaluating tuned tau={ALPHA_TO_TUNE} model ===")
        evaluate_tuned(series_id, best_params, alpha=ALPHA_TO_TUNE)