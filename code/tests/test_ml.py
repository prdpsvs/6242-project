"""Tests for ml_models (fixture data — small, just checks no crashes)."""
from datetime import date
from code.orchestrator.contracts import FaersQuery
from code.data_ingest.faers_client import fetch
from code.drug_normalization.standardizer import standardize
from code.ml_models.features import featurize
from code.ml_models.baseline import train


def _setup():
    q = FaersQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), live=False)
    records = fetch(q)
    drug_map = standardize(records, live=False)
    return records, drug_map


def test_featurize_shape():
    records, drug_map = _setup()
    X, y = featurize(records, drug_map)
    assert len(X) == len(y)
    assert len(X) == len(records)


def test_feature_columns_present():
    records, drug_map = _setup()
    X, y = featurize(records, drug_map)
    for col in ["age", "sex_m", "n_suspect_drugs", "n_reactions"]:
        assert col in X.columns, f"Missing column: {col}"


def test_train_returns_models():
    records, drug_map = _setup()
    X, y = featurize(records, drug_map)
    models = train(X, y)
    assert isinstance(models.aucs, dict)
    assert "serious" in models.aucs
