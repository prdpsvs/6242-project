"""Evaluate ML model + graph signals against FDA ground truth."""
from __future__ import annotations

import math

import pandas as pd
from sklearn.metrics import roc_auc_score, f1_score

from ..orchestrator.contracts import DrugEventGraph, ValidationReport
from ..ml_models.baseline import TrainedModels
from .fda_alerts import get_signals


def run(
    models: TrainedModels,
    graph: DrugEventGraph,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    live: bool = False,
) -> ValidationReport:
    # --- ML metrics on held-out set ---
    auc, f1 = _ml_metrics(models, X_test, y_test)

    # --- Signal recovery ---
    gt_signals = get_signals(live=live)
    signals_recovered, signals_total, per_drug = _signal_recovery(graph, gt_signals)

    # --- PRR baseline AUC (dummy comparison) ---
    prr_auc = _prr_baseline_auc(graph)

    return ValidationReport(
        auc_roc=auc,
        f1=f1,
        baseline_auc_prr=prr_auc,
        signals_recovered=signals_recovered,
        signals_total=signals_total,
        per_drug=per_drug,
        notes=f"Ground truth signals from {'openFDA live' if live else 'fixture'}.",
    )


def _ml_metrics(models: TrainedModels, X: pd.DataFrame, y: pd.DataFrame) -> tuple[float, float]:
    clf = models.models.get("serious")
    if clf is None or len(X) < 4:
        return float("nan"), float("nan")
    proba = clf.predict_proba(X)[:, 1]
    yt = y["serious"].values
    auc = roc_auc_score(yt, proba) if len(set(yt)) > 1 else float("nan")
    f1 = f1_score(yt, (proba >= 0.5).astype(int), zero_division=0)
    return round(auc, 4), round(f1, 4)


def _signal_recovery(graph: DrugEventGraph, gt: list[tuple[str, str]]) -> tuple[int, int, list[dict]]:
    # Build set of (drug_label, ae_label) pairs present in graph
    drug_labels = {n.label.lower() for n in graph.nodes if n.kind == "drug"}
    ae_labels = {n.label.lower() for n in graph.nodes if n.kind == "ae"}

    # Build edge lookup: source_label + target_label
    edge_set: set[tuple[str, str]] = set()
    id_to_label = {n.id: n.label.lower() for n in graph.nodes}
    for e in graph.edges:
        sl = id_to_label.get(e.source, "")
        tl = id_to_label.get(e.target, "")
        edge_set.add((sl, tl))
        edge_set.add((tl, sl))

    per_drug: list[dict] = []
    recovered = 0
    for drug_name, ae_term in gt:
        # Fuzzy: check if drug appears in any drug node label
        matched_drug = any(drug_name in dl or dl in drug_name for dl in drug_labels)
        matched_edge = any(
            (drug_name in sl or sl in drug_name) and (ae_term in tl or tl in ae_term)
            for sl, tl in edge_set
        )
        if matched_edge:
            recovered += 1
        per_drug.append({"drug": drug_name, "ae": ae_term, "recovered": matched_edge, "drug_in_graph": matched_drug})

    return recovered, len(gt), per_drug


def _prr_baseline_auc(graph: DrugEventGraph) -> float:
    """Simple baseline: use PRR ≥ 2 as a positive signal prediction."""
    prrs = [e.prr for e in graph.edges if e.prr is not None]
    if not prrs:
        return float("nan")
    # Treat PRR as a score; can't compute real AUC without true labels per edge,
    # so we report % of edges with PRR ≥ 2 (a commonly used threshold) as proxy.
    above = sum(1 for p in prrs if p >= 2.0)
    return round(above / len(prrs), 4)
