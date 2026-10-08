"""Phase 2: Optuna hyperparameter tuning, then final quantile model training."""

import numpy as np
import lightgbm as lgb
import optuna
from sklearn.model_selection import TimeSeriesSplit

from src.analysis.feature_matrix import build_features

optuna.logging.set_verbosity(optuna.logging.WARNING)

FEATURE_COLS = ["settlement_period", "day_of_week", "month", "lag_1d", "lag_1w", "rolling_std_7d"]


#Pinball (quantile) loss for a given tau — the metric quantile models are actually scored on, not MAE
def pinball_loss(y_true, y_pred, tau):
    diff = y_true - y_pred
    return np.mean(np.maximum(tau * diff, (tau - 1) * diff))

#Tunes for a SPECIFIC quantile (alpha),both the model and the scoring metric use the same alpha, so they can never silently mismatch
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
            losses.append(pinball_loss(y.iloc[test_idx].values, pred, alpha))
        return np.mean(losses)

    # seed makes the search repeatable: same data + same seed = same best params
    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)
    print(f"  Best trial pinball loss (tau={alpha}): {study.best_value:.3f}")
    print(f"  Best params: {study.best_params}")
    return study.best_params

#Re-run TimeSeriesSplit CV with tuned hyperparameters for one quantile; the naive baseline is scored on the SAME rows as the model
def evaluate_tuned(series_id: str, best_params: dict, alpha: float, n_splits: int = 5):
    df = build_features(series_id)
    X, y = df[FEATURE_COLS], df["y"]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    model_maes, pers_maes = [], []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = lgb.LGBMRegressor(objective="quantile", alpha=alpha, verbose=-1, **best_params)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        # persistence = yesterday's price (lag_1d), on the same test rows
        err_model = np.abs(y_test.values - pred)
        err_pers = np.abs(y_test.values - X_test["lag_1d"].values)
        ok = ~np.isnan(err_pers)
        m, p = err_model[ok].mean(), err_pers[ok].mean()
        model_maes.append(m)
        pers_maes.append(p)
        print(f"  Fold {fold}: tau={alpha} MAE=£{m:.2f} | persistence £{p:.2f}")

    avg_m, avg_p = np.mean(model_maes), np.mean(pers_maes)
    print(f"  Avg tuned tau={alpha} MAE: £{avg_m:.2f} vs persistence £{avg_p:.2f} "
          f"-> {100 * (avg_p - avg_m) / avg_p:.1f}% better")
    return avg_m

#Tune one quantile (set via ALPHA_TO_TUNE) for both series with Optuna, then evaluate the tuned model
if __name__ == "__main__":
    ALPHA_TO_TUNE = 0.5   # only P50 feeds the optimiser; use 0.1 / 0.9 only if you re-check calibration

    for series_id in ["gb_day_ahead_price", "gb_imbalance_price"]:
        print(f"\n=== {series_id}: tuning tau={ALPHA_TO_TUNE} ===")
        df = build_features(series_id)
        X, y = df[FEATURE_COLS], df["y"]
        best_params = tune_hyperparameters(X, y, alpha=ALPHA_TO_TUNE, n_trials=30)
        print(f"  Copy-paste: P50_PARAMS = {best_params}")

        print(f"\n=== {series_id}: evaluating tuned tau={ALPHA_TO_TUNE} model ===")
        evaluate_tuned(series_id, best_params, alpha=ALPHA_TO_TUNE)