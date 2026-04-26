"""XGBoost / LightGBM baseline serious-outcome predictors."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score
from xgboost import XGBClassifier

from ..orchestrator import config

_TARGETS = ["serious", "hospitalization", "death"]


@dataclass
class TrainedModels:
    models: dict = field(default_factory=dict)   # target -> fitted model
    aucs: dict = field(default_factory=dict)      # target -> AUC on test
    f1s: dict = field(default_factory=dict)


def train(X: pd.DataFrame, y: pd.DataFrame) -> TrainedModels:
    """Train one XGBClassifier per outcome target. Returns TrainedModels."""
    result = TrainedModels()
    if len(X) < 10:
        # Too few records to train (fixture-only tiny run)
        for t in _TARGETS:
            result.models[t] = None
            result.aucs[t] = float("nan")
            result.f1s[t] = float("nan")
        return result

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_SEED
    )

    for target in _TARGETS:
        yt_tr = y_tr[target].values
        yt_te = y_te[target].values
        n_pos = yt_tr.sum()
        if n_pos < 2:
            result.models[target] = None
            result.aucs[target] = float("nan")
            result.f1s[target] = float("nan")
            continue
        scale = max(1.0, (len(yt_tr) - n_pos) / n_pos)
        clf = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            scale_pos_weight=scale,
            random_state=config.RANDOM_SEED,
            eval_metric="logloss",
            verbosity=0,
        )
        clf.fit(X_tr, yt_tr)
        proba = clf.predict_proba(X_te)[:, 1]
        auc = roc_auc_score(yt_te, proba) if len(set(yt_te)) > 1 else float("nan")
        preds = (proba >= 0.5).astype(int)
        f1 = f1_score(yt_te, preds, zero_division=0)
        result.models[target] = clf
        result.aucs[target] = round(auc, 4)
        result.f1s[target] = round(f1, 4)

    return result


def predict_one(models: TrainedModels, X_row: pd.DataFrame) -> dict[str, float]:
    """Predict probabilities for a single feature row dict."""
    result = {}
    for target in _TARGETS:
        clf = models.models.get(target)
        if clf is None:
            result[f"p_{target}"] = float("nan")
        else:
            result[f"p_{target}"] = round(float(clf.predict_proba(X_row)[:, 1][0]), 4)
    return result
