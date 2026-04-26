# Interactive Drug Adverse Event Analysis & Prediction Platform — Project Plan

**Team 217** — Pradeep Srikakolapu, Sharath Kashetty, Sunil Mannuru
**Course:** CSE 6242 — Spring 2026

---

## 1. Guiding Principles

1. **No persistent storage in production runs.** All datasets are fetched live from public REST APIs at runtime when `--live` is passed. Only in‑memory caches within a single process lifetime. No Parquet/CSV/SQLite checkpoints on disk.
1a. **Development fixtures are allowed and committed.** A small JSON fixture set lives at `code/data_ingest/fixtures/` and is used by default (no `--live` flag). This avoids hammering openFDA during development and gives every team member a deterministic dataset. Fixtures are **not** the production data path — passing `--live` switches to real APIs.
2. **All code lives under `code/`.** No source files outside this folder.
3. **Strict modular ownership.** Each module is owned by one person and exposes a typed contract (Pydantic models). Modules communicate **only** through these contracts — never via shared files or globals.
4. **A single orchestrator** (`code/orchestrator/runner.py`) wires modules together, owned jointly. Nobody edits another person's module without a contract change agreed in writing.
5. **API-first.** Replace the proposal's bulk-Spark plan with streaming, paginated, on-demand API calls. Spark is replaced by `pandas` + `pyarrow` in-memory + async batching.

---

## 2. Data Sources (APIs only — no downloads)

| # | Source | Endpoint (base) | What we pull | Owner |
|---|--------|-----------------|--------------|-------|
| 1 | **openFDA Drug Adverse Events (FAERS)** | `https://api.fda.gov/drug/event.json` | Adverse event reports, reactions, demographics, outcomes, time-windowed | Pradeep |
| 2 | **openFDA Drug Labeling** | `https://api.fda.gov/drug/label.json` | Drug indications, warnings, boxed warnings (for validation) | Sharath |
| 3 | **openFDA Drug Enforcement** | `https://api.fda.gov/drug/enforcement.json` | FDA recalls / safety alerts (ground truth for validation) | Sharath |
| 4 | **RxNorm REST API (NLM)** | `https://rxnav.nlm.nih.gov/REST/` | Drug name → RxCUI normalization, ingredient lookup, brand→generic | Sharath |
| 5 | **RxNav Interaction API** | `https://rxnav.nlm.nih.gov/REST/interaction/` | Known DDI list (validation set for our DDI predictions) | Sharath |
| 6 | **MeSH / UMLS (optional)** | `https://id.nlm.nih.gov/mesh/` | MedDRA reaction term grouping (for clustering coarseness) | Pradeep |

**Rate limits:** openFDA = 240 req/min/IP without key, 120,000/day with key. RxNorm = no documented hard limit, be polite (≤ 20 req/s). All clients implement exponential backoff + per-host token bucket.

**No API keys are committed.** Keys (optional openFDA key) are read from environment variables (`OPENFDA_API_KEY`).

---

## 3. Module Ownership & Folder Layout

```
code/
├── orchestrator/                   [ALL — joint ownership]
│   ├── runner.py                   # main pipeline entrypoint
│   ├── contracts.py                # Pydantic models = inter-module API
│   └── config.py                   # endpoints, rate limits, run params
│
├── data_ingest/                    [PRADEEP]
│   ├── faers_client.py             # async openFDA paginated client
│   ├── cleaner.py                  # in-memory dedup (CASENUM), null handling
│   └── normalizer.py               # adapts raw FAERS JSON → FaersRecord
│
├── drug_normalization/             [SHARATH]
│   ├── rxnorm_client.py            # name → RxCUI, ingredient resolution
│   └── standardizer.py             # batch standardize a list of drug strings
│
├── graph_analytics/                [PRADEEP + SUNIL]
│   ├── graph_builder.py            # build drug↔AE bipartite + drug-drug projection
│   ├── community.py                # Louvain (networkx + python-louvain)
│   └── metrics.py                  # PRR, ROR, IC (disproportionality baselines)
│
├── ml_models/                      [SHARATH (baseline) + PRADEEP/SHARATH (tuning)]
│   ├── features.py                 # feature engineering from FaersRecord stream
│   ├── baseline.py                 # XGBoost/LightGBM serious-outcome predictor
│   ├── tuning.py                   # Optuna hyperparameter search
│   └── explain.py                  # SHAP value computation
│
├── validation/                     [SHARATH]
│   ├── fda_alerts.py               # pulls enforcement + labeling for ground truth
│   └── evaluate.py                 # AUC-ROC / F1 / signal-validation metrics
│
├── visualization/                  [SUNIL]
│   ├── server/
│   │   ├── app.py                  # FastAPI: serves JSON to D3 frontend
│   │   └── routes.py               # /graph, /predict, /filter, /search
│   └── frontend/
│       ├── index.html
│       ├── network.js              # D3 force-directed network
│       ├── filters.js              # demographics/time/severity filters
│       └── styles.css
│
├── scalability/                    [PRADEEP]
│   └── benchmark.py                # wall-clock vs N records, vs concurrency
│
├── user_study/                     [SUNIL]
│   └── survey_runner.py            # collects responses in-memory; exports JSON
│
└── tests/                          [each owner writes tests for own module]
    ├── test_contracts.py
    ├── test_faers_client.py
    └── ...
```

---

## 4. Inter-Module Contracts (the *only* allowed integration surface)

Defined in `code/orchestrator/contracts.py` as Pydantic v2 models. Any field change requires a PR comment from the affected downstream owner.

### 4.1 `FaersQuery` — orchestrator → data_ingest
```python
class FaersQuery(BaseModel):
    date_from: date              # received date lower bound
    date_to: date
    drug_names: list[str] | None # None = all drugs
    serious_only: bool = False
    max_records: int = 50_000    # guardrail
    page_size: int = 100         # openFDA max
```

### 4.2 `FaersRecord` — data_ingest → everyone
```python
class FaersRecord(BaseModel):
    safety_report_id: str
    received_date: date
    patient_age: float | None
    patient_sex: Literal["M","F","U"] | None
    country: str | None
    drugs: list[DrugMention]     # raw + role (suspect/concomitant)
    reactions: list[str]         # MedDRA preferred terms
    outcomes: list[str]          # death, hospitalization, disability, ...
    serious: bool
```

### 4.3 `StandardizedDrug` — drug_normalization → graph_analytics, ml_models
```python
class StandardizedDrug(BaseModel):
    raw_name: str
    rxcui: str | None
    ingredient_rxcui: str | None
    ingredient_name: str | None
    confidence: float            # 0..1, fuzzy-match score
```

### 4.4 `DrugEventGraph` — graph_analytics → visualization, ml_models
```python
class GraphNode(BaseModel):
    id: str                      # "drug:RXCUI" or "ae:MEDDRA"
    kind: Literal["drug","ae"]
    label: str
    degree: int
    community: int | None

class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float                # co-occurrence count
    prr: float | None
    ror: float | None

class DrugEventGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: dict                   # build params, record count, build_time_s
```

### 4.5 `PredictionRequest` / `PredictionResponse` — visualization → ml_models
```python
class PredictionRequest(BaseModel):
    drugs: list[str]             # raw names; standardized internally
    age: float | None
    sex: Literal["M","F","U"] | None

class PredictionResponse(BaseModel):
    p_serious: float
    p_hospitalization: float
    p_death: float
    top_features: list[tuple[str, float]]  # SHAP contributions
```

### 4.6 `ValidationReport` — validation → orchestrator (and final report)
```python
class ValidationReport(BaseModel):
    auc_roc: float
    f1: float
    baseline_auc_prr: float
    signals_recovered: int       # vs FDA enforcement set
    signals_total: int
    per_drug: list[dict]
```

---

## 5. Orchestrator (Runner)

`code/orchestrator/runner.py` exposes one CLI:

```
python -m code.orchestrator.runner \
    --mode {pipeline|serve|benchmark|validate} \
    --date-from 2023-01-01 --date-to 2024-12-31 \
    --drugs "warfarin,aspirin" \
    --max-records 50000
```

**`pipeline` mode flow (synchronous, in-memory):**

1. `data_ingest.faers_client.fetch(FaersQuery)` → `Iterator[FaersRecord]`
2. `drug_normalization.standardizer.standardize_stream(records)` → records with `StandardizedDrug` attached
3. `graph_analytics.graph_builder.build(records)` → `DrugEventGraph`
4. `graph_analytics.community.detect(graph)` → graph with `community` populated
5. `ml_models.features.featurize(records)` → `(X, y)` arrays in RAM
6. `ml_models.baseline.train(X, y)` → fitted model object (held in process memory only)
7. `validation.evaluate.run(model, graph)` → `ValidationReport`
8. Hand graph + model to `visualization.server.app` (in-process) for `serve` mode.

**`serve` mode** runs steps 1–6 once on startup, then exposes FastAPI on `:8000`. Subsequent user filter/search requests re-slice the in-memory graph; new prediction requests run the in-memory model.

---

## 6. Per-Person Plan (mapped to proposal Gantt)

### Pradeep — Data + Graph + Scalability
| Wk | Deliverable | Module |
|----|-------------|--------|
| 2–4 | Async openFDA client with backoff, pagination, in-memory dedup | `data_ingest/` |
| 4–6 | Bipartite graph build + Louvain community detection | `graph_analytics/graph_builder.py`, `community.py` |
| 7–9 | Joint hyperparameter tuning (Optuna runner) | `ml_models/tuning.py` |
| 10–11 | Scalability benchmarks: wall-clock vs records, concurrency sweep | `scalability/benchmark.py` |

### Sharath — Standardization + ML + Validation
| Wk | Deliverable | Module |
|----|-------------|--------|
| 3–4 | RxNorm async client + fuzzy fallback | `drug_normalization/` |
| 4–6 | XGBoost/LightGBM baseline + PRR/ROR baseline metrics | `ml_models/baseline.py`, `graph_analytics/metrics.py` |
| 7–9 | Hyperparameter tuning + SHAP explanations | `ml_models/tuning.py`, `explain.py` |
| 9–10 | FDA enforcement / labeling validation pipeline | `validation/` |

### Sunil — Visualization + UX
| Wk | Deliverable | Module |
|----|-------------|--------|
| 4–6 | Joint graph build (consume Pradeep's graph) | `graph_analytics/` (read-only) |
| 5–7 | Prototype D3 force-directed network + FastAPI bridge | `visualization/server/`, `visualization/frontend/` |
| 7–10 | Full dashboard: filters, drill-down, search, predictor panel | `visualization/frontend/` |
| 10–11 | User study runner + evaluation summary | `user_study/` |

---

## 7. Dependencies (all open source)

```
httpx[http2]        # async API client
tenacity            # retry/backoff
pydantic>=2.0       # contracts
pandas, numpy
networkx, python-louvain
xgboost, lightgbm
optuna, shap
fastapi, uvicorn
cachetools          # in-memory TTL cache
pytest, pytest-asyncio
d3.js v7            # frontend (CDN, no build step)
```

Lockfile: `code/requirements.txt`. No conda env needed.

---

## 8. Risks & Mitigations Specific to API-Only Mode

| Risk | Mitigation |
|------|------------|
| openFDA rate limit blocks large pulls | Token-bucket limiter; obtain free API key (raises to 120k/day); time-window sharding for queries; concurrent host-friendly batching |
| Re-fetching same data every run is slow | Process-lifetime in-memory cache (`cachetools.TTLCache`), keyed by `FaersQuery` hash. Cleared on process exit (still "no persistent storage"). |
| RxNorm latency for 1000s of unique names | `asyncio.gather` with semaphore (≤ 20 in-flight); fuzzy local fallback using `rapidfuzz` against the in-memory RxCUI cache built so far |
| Demo reproducibility without disk | Runner accepts `--seed` and `--snapshot-query` so any reviewer can re-run the same query window and get the same data live |
| Network outage during demo | `serve` mode preloads on startup; if the API is down at startup we fail fast with a clear message (acceptable per "no persistent storage" rule) |

---

## 9. Definition of Done (per checkpoint)

**Midterm (Wk 6)**
- `pipeline` mode runs end-to-end on ≥ 50k FAERS records pulled live, in < 10 min.
- Graph + Louvain communities returned through `DrugEventGraph` contract.
- Baseline XGBoost AUC reported.
- Prototype D3 network renders the live graph with one filter (date range).

**Final (Wk 12)**
- `pipeline` runs on ≥ 500k records (sharded queries) in < 60 min.
- Tuned model beats PRR baseline AUC by ≥ 5 points.
- Dashboard supports drug search, demographic + severity + time filters, drill-down, and prediction panel.
- `ValidationReport` shows ≥ X% of FDA enforcement signals recovered (X set after first validation run).
- 5–10 person user study summary exported.

---

## 10. Next Step

Once this plan is approved, we "double-click" into each module in this order, producing one detailed design doc per module:

1. `data_ingest/` (Pradeep) — openFDA query strategy & dedup logic
2. `drug_normalization/` (Sharath) — RxNorm matching & fuzzy fallback
3. `graph_analytics/` (Pradeep + Sunil) — graph schema & Louvain params
4. `ml_models/` (Sharath) — feature set & label definition
5. `visualization/` (Sunil) — wireframes & FastAPI route spec
6. `validation/` (Sharath) — FDA ground-truth assembly
7. `scalability/` (Pradeep) — benchmark matrix
8. `orchestrator/` — final wiring & CLI surface
