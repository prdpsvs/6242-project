"""SHAP explanations for trained XGBoost models."""
from __future__ import annotations

import pandas as pd

try:
    import shap as shap_lib
    _HAS_SHAP = True
except ImportError:
    _HAS_SHAP = False

from .baseline import TrainedModels


def top_features(models: TrainedModels, X: pd.DataFrame, target: str = "serious",
                 top_n: int = 10) -> list[tuple[str, float]]:
    """Return top_n (feature, mean_abs_shap) pairs for the given target model."""
    clf = models.models.get(target)
    if clf is None or not _HAS_SHAP:
        # Fallback: use feature_importances_ from XGBoost
        if clf is not None and hasattr(clf, "feature_importances_"):
            pairs = sorted(zip(X.columns, clf.feature_importances_), key=lambda x: x[1], reverse=True)
            return [(str(k), round(float(v), 4)) for k, v in pairs[:top_n]]
        return []

    explainer = shap_lib.TreeExplainer(clf)
    sample = X.iloc[:min(200, len(X))]
    shap_values = explainer.shap_values(sample)
    mean_abs = pd.Series(
        abs(shap_values).mean(axis=0),
        index=X.columns,
    ).sort_values(ascending=False)
    return [(str(k), round(float(v), 4)) for k, v in mean_abs.head(top_n).items()]
