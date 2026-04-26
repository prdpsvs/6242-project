"""Louvain community detection on the drug–AE graph."""
from __future__ import annotations

import networkx as nx

try:
    import community as louvain_mod  # python-louvain
    _HAS_LOUVAIN = True
except ImportError:
    _HAS_LOUVAIN = False

from ..orchestrator.contracts import DrugEventGraph


def detect(nx_graph: nx.Graph, contract: DrugEventGraph) -> DrugEventGraph:
    """
    Run Louvain on nx_graph, attach community IDs to contract nodes.
    Falls back to connected-components if python-louvain not available.
    """
    if not nx_graph.nodes:
        return contract

    if _HAS_LOUVAIN:
        partition: dict[str, int] = louvain_mod.best_partition(nx_graph)
    else:
        partition = {}
        for idx, comp in enumerate(nx.connected_components(nx_graph)):
            for node in comp:
                partition[node] = idx

    updated_nodes = []
    for node in contract.nodes:
        updated_nodes.append(node.model_copy(update={"community": partition.get(node.id)}))

    meta = dict(contract.meta)
    meta["n_communities"] = len(set(partition.values())) if partition else 0

    return DrugEventGraph(nodes=updated_nodes, edges=contract.edges, meta=meta)
