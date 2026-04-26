"""Tests for graph_analytics (fixture data)."""
from datetime import date
from code.orchestrator.contracts import FaersQuery
from code.data_ingest.faers_client import fetch
from code.drug_normalization.standardizer import standardize
from code.graph_analytics.graph_builder import build
from code.graph_analytics.community import detect


def _get_records():
    q = FaersQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), live=False)
    return fetch(q)


def test_graph_builds():
    records = _get_records()
    drug_map = standardize(records, live=False)
    nx_g, g = build(records, drug_map)
    assert len(g.nodes) > 0
    assert len(g.edges) > 0


def test_graph_has_drug_and_ae_nodes():
    records = _get_records()
    drug_map = standardize(records, live=False)
    _, g = build(records, drug_map)
    kinds = {n.kind for n in g.nodes}
    assert "drug" in kinds
    assert "ae" in kinds


def test_community_detection():
    records = _get_records()
    drug_map = standardize(records, live=False)
    nx_g, g = build(records, drug_map)
    g2 = detect(nx_g, g)
    # At least some nodes should have community assigned
    assigned = [n for n in g2.nodes if n.community is not None]
    assert len(assigned) > 0
