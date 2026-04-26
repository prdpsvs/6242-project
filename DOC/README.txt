================================================================================
  Interactive Drug Adverse Event Analysis and Prediction Platform
  Team 217 | CSE 6242 — Spring 2026 | Georgia Tech
  Authors: Venkata Satya Pradeep Srikakolapu, Sharath Kashetty, Sunil Mannuru
================================================================================

DESCRIPTION
-----------
This system is a live, API-driven pharmacovigilance platform that:

1. Ingests FDA adverse event reports in real time from the openFDA FAERS API
   (no bulk downloads required).
2. Normalizes drug names to canonical RxNorm ingredients via the NLM RxNav API.
3. Builds a bipartite drug–adverse event graph and computes Proportional
   Reporting Ratio (PRR) and Reporting Odds Ratio (ROR) safety signals on
   every drug–event edge.
4. Detects drug communities (drugs sharing similar adverse event profiles) using
   the Louvain algorithm.
5. Trains an XGBoost model to predict individual patient risk (P_serious,
   P_hospitalization, P_death) with SHAP feature explanations.
6. Validates detected signals against 7 known FDA drug–event alert pairs.
7. Serves an interactive D3.js dashboard at http://127.0.0.1:8000 that lets
   users explore the network, filter by community, search by drug name, and
   run per-patient risk predictions.

All data is held in process memory only. No files are written to disk during
a run. Restarting the server triggers a fresh API pull.


INSTALLATION
------------
Requirements: Python 3.10 or later (developed and tested on Python 3.13).

Step 1 — Create and activate a virtual environment:

    python -m venv .venv

    # Windows:
    .\.venv\Scripts\activate

    # macOS / Linux:
    source .venv/bin/activate

Step 2 — Install dependencies:

    pip install -r code/requirements.txt

Step 3 — (Optional) Set your openFDA API key to raise the rate limit from
240 req/min to 120,000/day:

    # Windows PowerShell:
    $env:OPENFDA_API_KEY = "your_key_here"

    # macOS / Linux:
    export OPENFDA_API_KEY="your_key_here"

    Get a free key at: https://open.fda.gov/apis/authentication/

No other API keys are required. The RxNorm NLM API is free and unauthenticated.


EXECUTION
---------
All commands are run from the project root directory.

--- Fixture mode (offline, instant, uses 20 pre-saved records) ---

    python -m code.orchestrator.runner pipeline

Expected output:
    Step 1/6: Fetching FAERS records  → 20 records (0.0s)
    Step 2/6: Normalizing drug names  → 18 unique drugs (0.0s)
    Step 3/6: Building drug–AE graph  → 34 nodes · 31 edges (0.0s)
    Step 4/6: Louvain community det.  → 7 communities (0.0s)
    Step 5/6: Training ML models      → AUC serious=1.0 hosp=0.5 death=nan (0.7s)
    Step 6/6: Running validation      → Signals 0/7 (0.0s)

--- Live mode (queries real openFDA API) ---

    python -m code.orchestrator.runner pipeline --live --max-records 50

Fetches 50 live FAERS records (~10 seconds with default rate limiting).
For larger datasets (better signal detection), use --max-records 5000 or higher.

--- Dashboard mode (recommended for interactive exploration) ---

    python -m code.orchestrator.runner serve

Opens the interactive dashboard at:  http://127.0.0.1:8000

With live data:
    python -m code.orchestrator.runner serve --live --max-records 5000

The server pre-loads all data on startup, then remains interactive. All API
calls, graph construction, and model training happen once at startup.
Subsequent browser requests re-use in-memory data with no additional API calls.

--- Stop the server ---
    Press Ctrl+C in the terminal, or run:
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess) -Force

--- Run tests ---
    python -m pytest code/tests/ -v --tb=short
    Expected: 14 passed


DASHBOARD FEATURES
------------------
- Force-directed drug–adverse event network graph (D3.js v7)
- Blue circles = drug nodes, orange circles = adverse event nodes
- Red edges = high PRR signal (≥ 5); orange edges = moderate signal (≥ 2)
- Click a drug node to highlight its neighborhood and see top AE neighbors by PRR
- Double-click to drill into the neighborhood subgraph
- Filter by community using the dropdown
- Search for a specific drug by name
- Top Safety Signals panel: all PRR ≥ 2 drug–event pairs, sorted by PRR
- Prediction panel: enter patient age, sex, and drug list to get risk scores
- Stats panel: graph metadata and model AUC values


DEMO VIDEO
----------

FILE STRUCTURE
--------------
code/
  orchestrator/     — Pipeline runner and Pydantic contracts
  data_ingest/      — openFDA async client, cleaner, normalizer
  drug_normalization/ — RxNorm async client, drug standardizer
  graph_analytics/  — Bipartite graph builder, Louvain community detection
  ml_models/        — XGBoost baseline, Optuna tuning, SHAP explanations
  validation/       — FDA ground-truth signal evaluation
  visualization/    — FastAPI server + D3.js frontend
  tests/            — 14 unit tests (pytest)
  requirements.txt  — Python dependencies


KNOWN LIMITATIONS
-----------------
- Signal detection is strongest with ≥ 1,000 records. With < 100 records,
  many PRR values will be None (insufficient denominator data).
- The ML model requires ≥ 100 records per class for meaningful AUC estimates.
  With small datasets, AUC values may show as None (not N/A — not a bug).
- openFDA rate limit: 240 req/min without API key; 120k/day with key.
  Large pulls (> 10,000 records) will take 30+ minutes without an API key.
- The dashboard is optimized for graphs up to ~2,000 nodes. Very large graphs
  (50,000+ records) may have slow D3 force simulation in the browser.


DEPENDENCIES (key packages)
----------------------------
httpx[http2]          Async HTTP client for API calls
tenacity              Exponential backoff / retry
pydantic>=2.0         Typed data contracts between modules
networkx              Graph construction and analytics
python-louvain        Louvain community detection
xgboost               Gradient-boosted tree classifier
shap                  SHAP explainability for ML predictions
optuna                Hyperparameter optimization
fastapi               REST API server
uvicorn               ASGI server
rapidfuzz             Fuzzy drug name matching fallback

Full list with pinned versions: code/requirements.txt
