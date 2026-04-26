# Presentation Notes — Sunil Mannuru
**Role: Visualization & Dashboard Development**
**Time: ~3 minutes**

---

## 🗺️ Poster Section Map — Know Before You Present

| Column | Sections (top → bottom) |
|---|---|
| **Left (Col 1)** | The Problem · Why It Matters · Data Sources · Data Characteristics |
| **Middle (Col 2)** | Our Approach · Key Algorithms · What Is New |
| **Right (Col 3)** | Drug–Adverse Event Network · Pipeline Run Results · Top Detected Safety Signals (PRR) · Method Comparison |
| **Footer** | Conclusion · Future Work · Tech Stack & Links |

> **📌 POSTER callouts below** tell you exactly which section to point at and when.

---

## Opening — The Interface Problem (30 sec)

> "Pradeep produces a graph with thousands of edges. Sharath produces risk scores and signal tables. None of that matters if nobody can use it. My job was to turn typed data contracts into something a clinician or analyst can explore in under 90 seconds — no manual, no training, no bulk download."

> 📌 **POSTER → Col 3: "Drug–Adverse Event Network"** (green header, top of right column) — point directly at the network SVG diagram. This is the centerpiece of what you built.

---

## What I Built (75 sec)

**FastAPI backend (server layer):**
- Six REST endpoints: `/graph`, `/graph/communities`, `/graph/drug/{label}`, `/predict`, `/stats`, `/validation`.
- All data lives in process memory after pipeline run — no database, no file system reads at query time.
- Key engineering challenge: **Python's stdlib JSON encoder rejects `float('nan')`** — XGBoost and scikit-learn occasionally produce NaN importance scores for features that never fire. Fixed with `_sanitize()` and `_safe()` helper functions that replace NaN/Inf with `null`/`0.0` before serialization, so the API never crashes on a real query.

> 📌 **POSTER → Col 2: "Key Algorithms"** (orange header) — point to the FastAPI / D3.js row in the tech stack column.

**D3.js v7 force-directed network (frontend):**
- Drug nodes (blue) and adverse event nodes (orange) laid out by force simulation.
- **Edge color encodes PRR tier:** red = PRR ≥ 5 (high signal), orange = PRR ≥ 2 (signal), gray = below threshold.
- **Edge width scales with PRR value.** Node radius scales with degree. Labels shown only for top-35th-percentile-degree nodes to avoid clutter.

> 📌 **POSTER → Col 3: "Drug–Adverse Event Network"** — point to the color legend (red/orange/gray edges) on the network diagram. Explain the encoding in one sentence.

- **Click a drug node** → non-neighbors dim to 15% opacity, sidebar shows the top-5 AE neighbors ranked by PRR. Double-click drills into the neighborhood subgraph.
- **Prediction panel:** enter age, sex, drug list → returns P(serious/hospitalization/death) as percentage bars with SHAP feature contributions ranked beneath.
- **Top Safety Signals panel:** all PRR ≥ 2 drug–AE pairs sorted descending, filterable.

> 📌 **POSTER → Col 3: "Top Detected Safety Signals (PRR)"** (orange header) — the table on the poster is exactly what the Top Safety Signals panel displays. Point to it.

---

## How It Fits the Whole Solution (30 sec)

> "The dashboard is the only user-facing layer. Everything Pradeep and Sharath built is invisible until it shows up here. The Pydantic contracts mean my frontend always knows the exact shape of the data — I never had to guess field names or handle missing keys in the UI."

> 📌 **POSTER → Col 2: "Our Approach"** (blue header) — point to Step 6 ("Dashboard / Serve") and trace back up to Step 1, showing your endpoint sits at the tip of the entire pipeline.
> If demoing live: click warfarin node → show sidebar PRR values → run a prediction → show SHAP bars.

---

## Key Results (30 sec)

- Informal usability test with **3 users**: all completed the full workflow (find drug → view AEs → run prediction) within **90 seconds** of first use — no instructions given.
- Dashboard handles up to **~2,000 nodes** smoothly; performance degrades beyond that due to force simulation cost (known limitation, listed as future work with WebGL renderer).
- The neighborhood highlight and Top Safety Signals panel were the two most-used features in the usability session.

> 📌 **POSTER → Col 3: "Pipeline Run Results"** (green header) — point to the Nodes/Edges row at 50k records to show the scale the dashboard handles.
> Then sweep to **Footer: "Future Work"** — point to the WebGL / scaling bullet.

---

## Closing Line (15 sec)

> "What we've built is the only system that combines live signal detection, community clustering, individual risk prediction, and interactive drill-down in a single deployable pipeline — no downloads, no setup beyond `pip install`, no stale data."

---

## Anticipated Questions

| Question | Answer |
|---|---|
| Why D3.js and not a library like Cytoscape.js? | D3 gives full control over encoding: edge color = PRR tier, edge width = PRR value, node radius = degree. Cytoscape's defaults would have required the same customization with more abstraction overhead. |
| What happens when the graph gets very large? | Node labels are suppressed below the 35th percentile degree. Beyond ~2,000 nodes the force simulation slows down. A WebGL-based renderer (e.g., sigma.js) is the planned fix. |
| Can a user filter by community? | The `/graph/communities` endpoint exposes community labels. Community-based filtering in the UI is implemented as a color overlay; a dedicated filter panel is listed as future work. |
