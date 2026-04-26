"""Tests for Pydantic contracts — ensures contract schema is stable."""
from datetime import date
from code.orchestrator.contracts import (
    FaersRecord, FaersQuery, DrugMention, StandardizedDrug,
    GraphNode, GraphEdge, DrugEventGraph, PredictionRequest, PredictionResponse, ValidationReport
)


def test_faers_record_minimal():
    r = FaersRecord(safety_report_id="test-001")
    assert r.serious is False
    assert r.drugs == []


def test_faers_record_full():
    r = FaersRecord(
        safety_report_id="test-002",
        received_date=date(2024, 1, 15),
        patient_age=67.0,
        patient_sex="F",
        drugs=[DrugMention(name="warfarin", role="suspect")],
        reactions=["Hemorrhage"],
        serious=True,
        hospitalization=True,
    )
    assert r.hospitalization is True
    assert r.drugs[0].name == "warfarin"


def test_faers_query_defaults():
    q = FaersQuery(date_from=date(2023, 1, 1), date_to=date(2024, 12, 31))
    assert q.max_records == 50_000
    assert q.live is False


def test_drug_event_graph():
    nodes = [
        GraphNode(id="drug:warfarin", kind="drug", label="warfarin", degree=3),
        GraphNode(id="ae:hemorrhage", kind="ae", label="Hemorrhage", degree=1),
    ]
    edges = [GraphEdge(source="drug:warfarin", target="ae:hemorrhage", weight=5.0, prr=3.2)]
    g = DrugEventGraph(nodes=nodes, edges=edges, meta={"n_records": 100})
    assert g.edges[0].prr == 3.2


def test_prediction_response():
    r = PredictionResponse(p_serious=0.8, p_hospitalization=0.6, p_death=0.1)
    assert r.top_features == []
