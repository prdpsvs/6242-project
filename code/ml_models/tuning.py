"""Optuna hyperparameter tuning for XGBoost models."""
from __future__ import annotations

import pandas as pd
from sklearn.model_selection import cross_val_score
from xgboost import XGBClassifier

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _HAS_OPTUNA = True
except ImportError:
    _HAS_OPTUNA = False

from ..orchestrator import config
from .baseline import TrainedModels, _TARGETS


def tune(X: pd.DataFrame, y: pd.DataFrame, n_trials: int = 30) -> TrainedModels:
    """
    Run Optuna HPO for each target. Falls back to baseline defaults if Optuna unavailable
    or if dataset is too small.
    """
    from .baseline import train  # late import to avoid circular
    if not _HAS_OPTUNA or len(X) < 50:
        return train(X, y)

    result = TrainedModels()
    for target in _TARGETS:
        yt = y[target].values
        if yt.sum() < 5:
            result.models[target] = None
            result.aucs[target] = float("nan")
            result.f1s[target] = float("nan")
            continue

        def objective(trial: "optuna.Trial") -> float:
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 2, 7),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "random_state": config.RANDOM_SEED,
                "eval_metric": "logloss",
                "verbosity": 0,
            }
            clf = XGBClassifier(**params)
            scores = cross_val_score(clf, X, yt, cv=3, scoring="roc_auc")
            return float(scores.mean())

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best = study.best_params
        best.update({"random_state": config.RANDOM_SEED, "eval_metric": "logloss", "verbosity": 0})
        clf = XGBClassifier(**best)
        clf.fit(X, yt)
        scores = cross_val_score(clf, X, yt, cv=3, scoring="roc_auc")
        result.models[target] = clf
        result.aucs[target] = round(float(scores.mean()), 4)
        result.f1s[target] = float("nan")  # full CV; compute separately if needed
    return result
