"""Tests for data_ingest (fixture path only — no network)."""
from datetime import date
from code.orchestrator.contracts import FaersQuery
from code.data_ingest.faers_client import fetch


def test_fetch_fixtures_returns_records():
    q = FaersQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), live=False)
    records = fetch(q)
    assert len(records) > 0


def test_records_have_drugs_and_reactions():
    q = FaersQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), live=False)
    records = fetch(q)
    for r in records:
        assert len(r.drugs) > 0, f"Record {r.safety_report_id} has no drugs"
        assert len(r.reactions) > 0, f"Record {r.safety_report_id} has no reactions"


def test_serious_records_present():
    q = FaersQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), live=False)
    records = fetch(q)
    assert any(r.serious for r in records)
