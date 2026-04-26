"""API routes.  State is injected by the orchestrator (no global singletons at import time)."""
from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from ...orchestrator.contracts import (
    DrugEventGraph, PredictionRequest, PredictionResponse, ValidationReport
)
from ...ml_models.baseline import TrainedModels, predict_one
from ...ml_models.features import featurize
from ...ml_models.explain import top_features
from ...orchestrator.contracts import FaersRecord, StandardizedDrug

router = APIRouter()

# Mutable state populated by init_state() before uvicorn starts
_state: dict = {
    "graph": None,
    "models": None,
    "records": [],
    "drug_map": {},
    "validation": None,
}


def init_state(
    graph: DrugEventGraph,
    models: TrainedModels,
    records: list,
    drug_map: dict,
    validation: ValidationReport | None,
) -> None:
    _state["graph"] = graph
    _state["models"] = models
    _state["records"] = records
    _state["drug_map"] = drug_map
    _state["validation"] = validation


# ---------- graph ----------

@router.get("/graph", response_model=DrugEventGraph)
def get_graph(
    community: Optional[int] = None,
    kind: Optional[str] = None,
    min_degree: int = 1,
):
    g: DrugEventGraph = _state["graph"]
    if g is None:
        raise HTTPException(503, "Graph not built yet")

    nodes = g.nodes
    if kind:
        nodes = [n for n in nodes if n.kind == kind]
    if community is not None:
        nodes = [n for n in nodes if n.community == community]
    if min_degree > 1:
        nodes = [n for n in nodes if n.degree >= min_degree]

    node_ids = {n.id for n in nodes}
    edges = [e for e in g.edges if e.source in node_ids and e.target in node_ids]

    return DrugEventGraph(nodes=nodes, edges=edges, meta=g.meta)


@router.get("/graph/communities")
def community_summary():
    g: DrugEventGraph = _state["graph"]
    if g is None:
        raise HTTPException(503, "Graph not built yet")
    from collections import Counter
    counts = Counter(n.community for n in g.nodes if n.community is not None)
    return [{"community": k, "size": v} for k, v in sorted(counts.items())]


@router.get("/graph/drug/{drug_label}")
def drug_neighborhood(drug_label: str, depth: int = 1):
    g: DrugEventGraph = _state["graph"]
    if g is None:
        raise HTTPException(503, "Graph not built yet")
    # Find matching drug nodes
    target_ids = {
        n.id for n in g.nodes
        if n.kind == "drug" and drug_label.lower() in n.label.lower()
    }
    if not target_ids:
        raise HTTPException(404, f"No drug matching '{drug_label}'")
    # Collect neighbors
    neighbor_ids = set(target_ids)
    for e in g.edges:
        if e.source in target_ids:
            neighbor_ids.add(e.target)
        if e.target in target_ids:
            neighbor_ids.add(e.source)
    nodes = [n for n in g.nodes if n.id in neighbor_ids]
    edges = [e for e in g.edges if e.source in neighbor_ids and e.target in neighbor_ids]
    return DrugEventGraph(nodes=nodes, edges=edges, meta=g.meta)


# ---------- prediction ----------

@router.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    models: TrainedModels = _state["models"]
    drug_map: dict = _state["drug_map"]
    if models is None:
        raise HTTPException(503, "Models not trained yet")

    # Build a minimal FaersRecord to featurize
    from ...orchestrator.contracts import FaersRecord, DrugMention
    mock_record = FaersRecord(
        safety_report_id="predict-request",
        patient_age=req.age,
        patient_sex=req.sex,
        drugs=[DrugMention(name=d.lower(), role="suspect") for d in req.drugs],
        reactions=["unknown"],
        serious=False,
    )
    X, _ = featurize([mock_record], drug_map)
    preds = predict_one(models, X)
    feats = top_features(models, X, target="serious")
    return PredictionResponse(
        p_serious=_safe(preds.get("p_serious")),
        p_hospitalization=_safe(preds.get("p_hospitalization")),
        p_death=_safe(preds.get("p_death")),
        top_features=feats,
    )


def _safe(v) -> float:
    """Replace NaN/Inf with 0 so JSON serialisation never fails."""
    import math
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return 0.0
    return float(v)


def _sanitize(d: dict) -> dict:
    """Recursively replace NaN/Inf floats in a dict with None."""
    import math
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and not math.isfinite(v):
            out[k] = None
        elif isinstance(v, dict):
            out[k] = _sanitize(v)
        else:
            out[k] = v
    return out


# ---------- stats ----------

@router.get("/stats")
def stats():
    g: DrugEventGraph = _state["graph"]
    models: TrainedModels = _state["models"]
    val: ValidationReport = _state["validation"]
    return _sanitize({
        "graph": g.meta if g else {},
        "ml_aucs": models.aucs if models else {},
        "validation": val.model_dump() if val else {},
        "n_records": len(_state["records"]),
    })


@router.get("/validation", response_model=ValidationReport)
def validation():
    val = _state["validation"]
    if val is None:
        raise HTTPException(503, "Validation not run yet")
    return val
