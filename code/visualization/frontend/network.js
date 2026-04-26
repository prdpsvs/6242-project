/**
 * network.js — D3 v7 force-directed network for drug–AE graph
 * Owner: Sunil Mannuru
 *
 * Key UX features:
 *  - Edge tooltips showing PRR, ROR, co-occurrence count
 *  - Node tooltips showing top connected nodes
 *  - Click node → highlight neighborhood, dim everything else
 *  - Top Signals panel loaded from graph edges (sorted by PRR)
 */
const API = "";  // same origin

let simulation, svgG, linkSel, nodeSel, labelSel;
let allNodes = [], allEdges = [], currentGraph = null;
let selectedNode = null;

const width  = () => document.getElementById("graph-svg").clientWidth  || 900;
const height = () => document.getElementById("graph-svg").clientHeight || 600;

// Color by community (cycle through palette)
const communityPalette = d3.schemeTableau10;
const communityColor = (c) =>
  c == null ? "#64748b" : communityPalette[c % communityPalette.length];

// ---- init SVG ----
const svg = d3.select("#graph-svg")
  .call(d3.zoom().scaleExtent([0.1, 8]).on("zoom", (e) => svgG.attr("transform", e.transform)));
svgG = svg.append("g");

// arrow marker for directed feel (optional visual)
svg.append("defs").append("marker")
  .attr("id", "arrow").attr("viewBox", "0 -5 10 10")
  .attr("refX", 18).attr("refY", 0)
  .attr("markerWidth", 6).attr("markerHeight", 6)
  .attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#475569");

const tooltip = document.getElementById("tooltip");

// ---- fetch + render ----
async function loadGraph(params = {}) {
  setBadge("loading", "Loading…");
  try {
    const qs = new URLSearchParams(params).toString();
    const resp = await fetch(`${API}/graph?${qs}`);
    if (!resp.ok) throw new Error(resp.statusText);
    currentGraph = await resp.json();
    allNodes = currentGraph.nodes;
    allEdges = currentGraph.edges;
    renderGraph(allNodes, allEdges);
    setBadge("ok", `${allNodes.length} nodes · ${allEdges.length} edges`);
  } catch (e) {
    setBadge("error", "API error: " + e.message);
  }
}

function renderGraph(nodes, edges) {
  svgG.selectAll("*").remove();

  const nodeById = new Map(nodes.map(n => [n.id, n]));
  const links = edges
    .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
    .map(e => ({ ...e, source: e.source, target: e.target }));

  const sizeScale = d3.scaleSqrt()
    .domain([1, d3.max(nodes, n => n.degree) || 1])
    .range([4, 20]);

  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(n => n.id).distance(60).strength(0.4))
    .force("charge", d3.forceManyBody().strength(-120))
    .force("center", d3.forceCenter(width() / 2, height() / 2))
    .force("collision", d3.forceCollide().radius(n => sizeScale(n.degree) + 3));

  linkSel = svgG.append("g").attr("class", "links")
    .selectAll("line").data(links).join("line")
    .attr("class", d => `link ${(d.prr != null && d.prr >= 2) ? "high-prr" : ""}`)
    .attr("stroke-width", d => {
      if (d.prr != null && d.prr >= 5) return 3;
      if (d.prr != null && d.prr >= 2) return 2;
      return Math.max(0.5, Math.log1p(d.weight) * 0.6);
    })
    .on("mouseover", showEdgeTooltip)
    .on("mousemove", moveTooltip)
    .on("mouseout",  hideTooltip);

  nodeSel = svgG.append("g").attr("class", "nodes")
    .selectAll("circle").data(nodes).join("circle")
    .attr("class", d => `node-${d.kind}`)
    .attr("r", d => sizeScale(d.degree))
    .attr("fill", d => communityColor(d.community))
    .attr("stroke", d => d.kind === "drug" ? "#93c5fd" : "#fdba74")
    .attr("stroke-width", 1.5)
    .call(d3.drag()
      .on("start", dragStart)
      .on("drag",  dragging)
      .on("end",   dragEnd))
    .on("mouseover", showNodeTooltip)
    .on("mousemove", moveTooltip)
    .on("mouseout",  hideTooltip)
    .on("click", onNodeClick);

  // Only label top-degree nodes to avoid clutter
  const labelThreshold = d3.quantile(nodes.map(n => n.degree).sort(d3.ascending), 0.65) || 2;
  labelSel = svgG.append("g").attr("class", "labels")
    .selectAll("text").data(nodes.filter(n => n.degree >= labelThreshold)).join("text")
    .attr("font-size", d => d.kind === "drug" ? "10px" : "9px")
    .attr("font-weight", d => d.kind === "drug" ? "600" : "400")
    .attr("fill", d => d.kind === "drug" ? "#bfdbfe" : "#fed7aa")
    .attr("dx", d => sizeScale(d.degree) + 3)
    .attr("dy", "0.35em")
    .text(d => d.label);

  // Deselect on background click
  svg.on("click", (e) => {
    if (e.target.tagName === "svg" || e.target.tagName === "g") clearHighlight();
  });

  simulation.on("tick", () => {
    linkSel
      .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    nodeSel.attr("cx", d => d.x).attr("cy", d => d.y);
    labelSel.attr("x", d => d.x).attr("y", d => d.y);
  });
}

// ---- neighbor highlighting ----
function highlightNeighborhood(d) {
  selectedNode = d.id;
  const neighborIds = new Set([d.id]);
  linkSel.each(lk => {
    const src = typeof lk.source === "object" ? lk.source.id : lk.source;
    const tgt = typeof lk.target === "object" ? lk.target.id : lk.target;
    if (src === d.id) neighborIds.add(tgt);
    if (tgt === d.id) neighborIds.add(src);
  });
  nodeSel.attr("opacity", n => neighborIds.has(n.id) ? 1.0 : 0.12);
  labelSel.attr("opacity", n => neighborIds.has(n.id) ? 1.0 : 0.08);
  linkSel.attr("opacity", lk => {
    const src = typeof lk.source === "object" ? lk.source.id : lk.source;
    const tgt = typeof lk.target === "object" ? lk.target.id : lk.target;
    return (src === d.id || tgt === d.id) ? 1.0 : 0.04;
  });
}

function clearHighlight() {
  selectedNode = null;
  nodeSel && nodeSel.attr("opacity", 1);
  labelSel && labelSel.attr("opacity", 1);
  linkSel && linkSel.attr("opacity", 1);
}

// ---- drag ----
function dragStart(e, d) { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
function dragging(e, d)   { d.fx = e.x; d.fy = e.y; }
function dragEnd(e, d)    { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }

// ---- node tooltip ----
function showNodeTooltip(e, d) {
  e.stopPropagation();
  const neighbors = [];
  if (linkSel) {
    linkSel.each(lk => {
      const src = typeof lk.source === "object" ? lk.source : lk.source;
      const tgt = typeof lk.target === "object" ? lk.target : lk.target;
      if (src.id === d.id) neighbors.push({ node: tgt, weight: lk.weight, prr: lk.prr });
      if (tgt.id === d.id) neighbors.push({ node: src, weight: lk.weight, prr: lk.prr });
    });
  }
  neighbors.sort((a, b) => (b.prr || 0) - (a.prr || 0));
  const connLabel = d.kind === "drug" ? "Top adverse events" : "Top associated drugs";
  const connRows = neighbors.slice(0, 5).map(nb => {
    const label = nb.node.label || nb.node.id;
    const prr   = nb.prr != null ? ` <span class="tt-prr">${nb.prr.toFixed(1)}×</span>` : "";
    return `<div class="tt-conn-row">• ${label}${prr}</div>`;
  }).join("") || "<div style='color:#64748b'>—</div>";

  tooltip.classList.remove("hidden");
  tooltip.innerHTML = `
    <b class="tt-title">${d.label}</b>
    <div class="tt-kind ${d.kind === 'drug' ? 'tt-drug' : 'tt-ae'}">${d.kind === 'drug' ? 'Drug' : 'Adverse Event'}</div>
    <div class="tt-stat"><span>Connections:</span> <b>${d.degree}</b></div>
    ${d.community != null ? `<div class="tt-stat"><span>Drug cluster:</span> <b>${d.community}</b></div>` : ""}
    <div class="tt-conn-label">${connLabel}:</div>
    ${connRows}
    <div class="tt-hint">Click to highlight · Double-click to drill in</div>
  `;
}

// ---- edge tooltip ----
function showEdgeTooltip(e, d) {
  e.stopPropagation();
  const src = typeof d.source === "object" ? d.source.label : d.source;
  const tgt = typeof d.target === "object" ? d.target.label : d.target;
  const prrStr = d.prr != null ? d.prr.toFixed(2) : "—";
  const rorStr = d.ror != null ? d.ror.toFixed(2) : "—";
  const signal = d.prr != null && d.prr >= 2
    ? `<div class="tt-signal-flag">⚠ Statistically significant (PRR ≥ 2)</div>` : "";
  tooltip.classList.remove("hidden");
  tooltip.innerHTML = `
    <b class="tt-title">${src} → ${tgt}</b>
    <div class="tt-stat"><span>Co-occurrences:</span> <b>${d.weight ?? "—"}</b></div>
    <div class="tt-stat"><span>PRR:</span> <b>${prrStr}</b> <span class="tt-hint-inline">(baseline = 1.0)</span></div>
    <div class="tt-stat"><span>ROR:</span> <b>${rorStr}</b></div>
    ${signal}
  `;
}

function moveTooltip(e) {
  const margin = 16;
  let x = e.clientX + margin;
  let y = e.clientY - margin;
  const tw = tooltip.offsetWidth || 240;
  if (x + tw > window.innerWidth) x = e.clientX - tw - margin;
  tooltip.style.left = x + "px";
  tooltip.style.top  = y + "px";
}
function hideTooltip() { tooltip.classList.add("hidden"); }

// ---- click: first click highlights neighborhood; second click drills into drug ----
async function onNodeClick(e, d) {
  e.stopPropagation();
  if (selectedNode === d.id && d.kind === "drug") {
    // Second click on same drug node → drill into neighborhood
    setBadge("loading", "Loading neighborhood…");
    try {
      const resp = await fetch(`${API}/graph/drug/${encodeURIComponent(d.label)}`);
      if (!resp.ok) throw new Error(resp.statusText);
      const sub = await resp.json();
      renderGraph(sub.nodes, sub.edges);
      loadSignalsFromEdges();
      setBadge("ok", `Neighborhood of "${d.label}" — ${sub.nodes.length} nodes · ${sub.edges.length} edges`);
    } catch (err) {
      setBadge("error", err.message);
    }
    return;
  }
  highlightNeighborhood(d);
}

// ---- stats ----
async function loadStats() {
  try {
    const resp = await fetch(`${API}/stats`);
    const data = await resp.json();
    const g = data.graph || {};
    const aucs = data.ml_aucs || {};
    document.getElementById("stats-content").innerHTML = `
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-val">${data.n_records ?? "—"}</div><div class="stat-label">Reports</div></div>
        <div class="stat-card"><div class="stat-val">${g.n_drug_nodes ?? "—"}</div><div class="stat-label">Drugs</div></div>
        <div class="stat-card"><div class="stat-val">${g.n_ae_nodes ?? "—"}</div><div class="stat-label">Adverse Events</div></div>
        <div class="stat-card"><div class="stat-val">${g.n_edges ?? "—"}</div><div class="stat-label">Edges</div></div>
        <div class="stat-card"><div class="stat-val">${g.n_communities ?? "—"}</div><div class="stat-label">Drug Clusters</div></div>
        <div class="stat-card"><div class="stat-val">${g.build_time_s != null ? g.build_time_s + "s" : "—"}</div><div class="stat-label">Build time</div></div>
      </div>
      <div class="auc-row">
        ML AUC — Serious: <b>${fmt(aucs.serious)}</b>&nbsp; Hosp: <b>${fmt(aucs.hospitalization)}</b>&nbsp; Death: <b>${fmt(aucs.death)}</b>
      </div>
    `;
  } catch {}
}

function fmt(v) { return v != null && !isNaN(v) ? (+v).toFixed(3) : "—"; }

// ---- top signals from graph edges ----
function loadSignalsFromEdges() {
  if (!allEdges.length && !linkSel) return;
  const edgeData = [];
  if (linkSel) {
    linkSel.each(d => edgeData.push(d));
  } else {
    edgeData.push(...allEdges);
  }
  const nodeLabel = new Map(allNodes.map(n => [n.id, { label: n.label, kind: n.kind }]));
  const sigs = edgeData
    .filter(e => e.prr != null && e.prr >= 2)
    .map(e => {
      const srcId = typeof e.source === "object" ? e.source.id : e.source;
      const tgtId = typeof e.target === "object" ? e.target.id : e.target;
      const src = nodeLabel.get(srcId);
      const tgt = nodeLabel.get(tgtId);
      if (!src || !tgt) return null;
      const drug = src.kind === "drug" ? src.label : tgt.label;
      const ae   = src.kind === "ae"   ? src.label : tgt.label;
      return { drug, ae, prr: e.prr, ror: e.ror, weight: e.weight };
    })
    .filter(Boolean)
    .sort((a, b) => b.prr - a.prr)
    .slice(0, 15);

  if (!sigs.length) {
    document.getElementById("signals-content").innerHTML =
      `<div class="sig-empty">No signals with PRR ≥ 2 in current view.<br>Try running with more records: <code>--live --max-records 5000</code></div>`;
    return;
  }
  document.getElementById("signals-content").innerHTML = sigs.map(s => {
    const cls = s.prr >= 5 ? "sig-high" : "sig-med";
    return `<div class="sig-row ${cls}">
      <div class="sig-names"><span class="sig-drug">${s.drug}</span><span class="sig-arrow">→</span><span class="sig-ae">${s.ae}</span></div>
      <div class="sig-stats"><span class="sig-prr" title="Proportional Reporting Ratio">PRR ${s.prr.toFixed(1)}</span><span class="sig-count">n=${s.weight ?? "—"}</span></div>
    </div>`;
  }).join("");
}

// ---- validation panel ----
async function loadValidation() {
  try {
    const resp = await fetch(`${API}/validation`);
    if (!resp.ok) return;
    const val = await resp.json();
    const rows = (val.per_drug || []).map(s =>
      `<div class="signal-row">
        <span class="val-pair">${s.drug} → ${s.ae}</span>
        <span class="${s.recovered ? "signal-ok" : "signal-miss"}">${s.recovered ? "✓ Found" : "✗ Missed"}</span>
      </div>`
    ).join("");
    const recRate = val.signals_total > 0 ? Math.round((val.signals_recovered / val.signals_total) * 100) : 0;
    document.getElementById("val-content").innerHTML = `
      <div class="val-summary">Recovered <b>${val.signals_recovered}/${val.signals_total}</b> known signals (${recRate}%)</div>
      <div style="margin-top:8px">${rows}</div>
      ${val.notes ? `<div style="margin-top:6px;font-size:0.72rem;color:#64748b">${val.notes}</div>` : ""}
    `;
  } catch {}
}

// ---- helpers ----
function setBadge(cls, text) {
  const b = document.getElementById("status-badge");
  b.className = `badge ${cls}`;
  b.textContent = text;
}

// ---- prediction panel ----
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-predict").addEventListener("click", async () => {
    const drugs = document.getElementById("pred-drugs").value
      .split(",").map(s => s.trim()).filter(Boolean);
    const age = parseFloat(document.getElementById("pred-age").value) || null;
    const sex = document.getElementById("pred-sex").value || null;
    if (!drugs.length) return;
    const el = document.getElementById("pred-result");
    el.classList.remove("hidden");
    el.innerHTML = "<div style='color:#64748b'>Running…</div>";
    try {
      const resp = await fetch(`${API}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drugs, age, sex })
      });
      if (!resp.ok) throw new Error(await resp.text());
      const r = await resp.json();
      el.innerHTML = `
        <div style="margin-bottom:6px;font-weight:600;color:#e2e8f0">Risk estimates</div>
        ${probBar("Serious outcome", r.p_serious, "#f59e0b")}
        ${probBar("Hospitalization", r.p_hospitalization, "#ef4444")}
        ${probBar("Death", r.p_death, "#7c3aed")}
        ${r.top_features && r.top_features.length ? `
          <div style="margin-top:10px;font-size:0.75rem;color:#94a3b8">Top contributing factors:</div>
          ${r.top_features.slice(0,4).map(([f,v]) =>
            `<div class="feat-row"><span>${f}</span><span class="feat-val">${(+v).toFixed(3)}</span></div>`
          ).join("")}
        ` : ""}
      `;
    } catch (err) {
      el.innerHTML = `<div style="color:#f87171">Error: ${err.message}</div>`;
    }
  });
});

function probBar(label, prob, color) {
  const pct = prob != null ? Math.round(prob * 100) : 0;
  return `<div class="pred-bar-wrap">
    <span class="pred-bar-label">${label}</span>
    <div class="pred-bar-bg"><div class="pred-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    <span class="pred-pct">${pct}%</span>
  </div>`;
}

// ---- community filter dropdown ----
async function loadCommunities() {
  try {
    const resp = await fetch(`${API}/graph/communities`);
    if (!resp.ok) return;
    const data = await resp.json();
    const sel = document.getElementById("community-filter");
    data.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.community;
      opt.textContent = `Cluster ${c.community} (${c.size} nodes)`;
      sel.appendChild(opt);
    });
  } catch {}
}

// ---- boot ----
window.addEventListener("load", async () => {
  await loadGraph();
  await Promise.all([loadStats(), loadValidation(), loadCommunities()]);
  // Load signals after graph is rendered (uses live edge data)
  setTimeout(loadSignalsFromEdges, 500);
});
