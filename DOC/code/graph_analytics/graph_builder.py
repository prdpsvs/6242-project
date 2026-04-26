"""Build drug–adverse-event bipartite graph from FaersRecords."""
from __future__ import annotations

import time
from collections import defaultdict

import networkx as nx

from ..orchestrator.contracts import DrugEventGraph, FaersRecord, GraphEdge, GraphNode, StandardizedDrug


def build(
    records: list[FaersRecord],
    drug_map: dict[str, StandardizedDrug],
    min_edge_weight: int = 1,
) -> tuple[nx.Graph, DrugEventGraph]:
    """
    Returns (nx_graph, DrugEventGraph contract object).
    nx_graph is kept for downstream community detection.
    """
    t0 = time.time()
    # co-occurrence counts
    cooc: dict[tuple[str, str], int] = defaultdict(int)
    drug_counts: dict[str, int] = defaultdict(int)
    ae_counts: dict[str, int] = defaultdict(int)
    drug_ae_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in records:
        drug_ids: list[str] = []
        for dm in rec.drugs:
            sd = drug_map.get(dm.name)
            did = f"drug:{sd.ingredient_rxcui or sd.raw_name}" if sd and sd.ingredient_rxcui else f"drug:{dm.name}"
            drug_ids.append(did)
            drug_counts[did] += 1

        for rxn in rec.reactions:
            ae_id = f"ae:{rxn.lower()}"
            ae_counts[ae_id] += 1
            for did in drug_ids:
                drug_ae_matrix[did][ae_id] += 1
                cooc[(did, ae_id)] += 1

    # Build networkx bipartite graph
    G = nx.Graph()
    for did, cnt in drug_counts.items():
        label = did.replace("drug:", "")
        G.add_node(did, kind="drug", label=label, count=cnt)
    for ae_id, cnt in ae_counts.items():
        label = ae_id.replace("ae:", "")
        G.add_node(ae_id, kind="ae", label=label, count=cnt)
    for (did, ae_id), weight in cooc.items():
        if weight >= min_edge_weight:
            G.add_edge(did, ae_id, weight=weight)

    # Compute PRR + ROR for each drug-AE pair
    N = len(records)
    nodes_out: list[GraphNode] = []
    edges_out: list[GraphEdge] = []

    for node_id, data in G.nodes(data=True):
        nodes_out.append(GraphNode(
            id=node_id,
            kind=data.get("kind", "drug"),
            label=data.get("label", node_id),
            degree=G.degree(node_id),
        ))

    for did, ae_id, edata in G.edges(data=True):
        w = edata.get("weight", 1)
        prr, ror = _disproportionality(did, ae_id, drug_ae_matrix, drug_counts, ae_counts, N)
        edges_out.append(GraphEdge(source=did, target=ae_id, weight=float(w), prr=prr, ror=ror))

    build_time = round(time.time() - t0, 3)
    graph_contract = DrugEventGraph(
        nodes=nodes_out,
        edges=edges_out,
        meta={
            "n_records": N,
            "n_drug_nodes": len(drug_counts),
            "n_ae_nodes": len(ae_counts),
            "n_edges": len(edges_out),
            "build_time_s": build_time,
        },
    )
    return G, graph_contract


def _disproportionality(
    did: str,
    ae_id: str,
    dae: dict,
    drug_counts: dict,
    ae_counts: dict,
    N: int,
) -> tuple[float | None, float | None]:
    """Proportional Reporting Ratio and Reporting Odds Ratio."""
    a = dae[did].get(ae_id, 0)
    if a < 3:
        return None, None  # too sparse
    drug_total = drug_counts.get(did, 0)
    ae_total = ae_counts.get(ae_id, 0)
    if drug_total == 0 or ae_total == 0:
        return None, None
    b = max(0, drug_total - a)   # drug without AE
    c = max(0, ae_total - a)     # AE without drug
    d = max(0, N - a - b - c)    # neither
    ab = a + b
    cd = c + d
    if ab == 0 or cd == 0:
        return None, None
    prr = (a / ab) / (c / cd) if cd > 0 and c > 0 else None
    ror_num = a * d
    ror_den = b * c
    ror = ror_num / ror_den if ror_den > 0 else None
    return round(prr, 3) if prr else None, round(ror, 3) if ror else None
