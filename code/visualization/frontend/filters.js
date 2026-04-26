/**
 * filters.js — Controls wiring: search, min-degree, node-kind, community
 * Owner: Sunil Mannuru
 * Note: predict panel and community population are handled in network.js
 */

// ---- apply filters ----
function applyFilters() {
  const params = {};
  const kind   = document.getElementById("node-kind").value;
  const minDeg = parseInt(document.getElementById("min-degree").value, 10);
  const comm   = document.getElementById("community-filter").value;
  if (kind)      params.kind = kind;
  if (minDeg > 1) params.min_degree = minDeg;
  if (comm)      params.community = comm;
  loadGraph(params).then(() => setTimeout(loadSignalsFromEdges, 300));
}

// ---- drug search ----
document.getElementById("btn-search").addEventListener("click", async () => {
  const q = document.getElementById("drug-search").value.trim();
  if (!q) return;
  setBadge("loading", `Searching ${q}…`);
  try {
    const resp = await fetch(`/graph/drug/${encodeURIComponent(q)}`);
    if (!resp.ok) throw new Error(resp.statusText);
    const sub = await resp.json();
    renderGraph(sub.nodes, sub.edges);
    setTimeout(loadSignalsFromEdges, 300);
    setBadge("ok", `Neighborhood of "${q}" — ${sub.nodes.length} nodes · ${sub.edges.length} edges`);
  } catch (e) {
    setBadge("error", "Not found: " + e.message);
  }
});

document.getElementById("btn-reset").addEventListener("click", () => {
  document.getElementById("drug-search").value = "";
  document.getElementById("node-kind").value = "";
  document.getElementById("min-degree").value = "1";
  document.getElementById("community-filter").value = "";
  loadGraph().then(() => setTimeout(loadSignalsFromEdges, 300));
});

// Filter inputs trigger on change
["node-kind", "community-filter", "min-degree"].forEach(id =>
  document.getElementById(id).addEventListener("change", applyFilters)
);

