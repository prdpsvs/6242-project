# Team 217 — Interactive Drug Adverse Event Analysis Platform

See [`../PLAN.md`](../PLAN.md) for the full project plan, ownership, and contracts.

## Quick start

```powershell
# 1. Create venv & install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r code/requirements.txt

# 2. Run end-to-end pipeline on dev fixtures (no network)
python -m code.orchestrator.runner pipeline

# 3. Run on real openFDA data
python -m code.orchestrator.runner pipeline --live --date-from 2023-01-01 --date-to 2024-12-31 --max-records 50000

# 4. Launch interactive dashboard (uses fixtures by default)
python -m code.orchestrator.runner serve
# then open http://localhost:8000

# 5. Live dashboard
python -m code.orchestrator.runner serve --live --max-records 20000

# 6. Validation against FDA enforcement signals
python -m code.orchestrator.runner validate --live

# 7. Scalability benchmark
python -m code.orchestrator.runner benchmark --live
```

## Folder layout

```
code/
├── orchestrator/        # ALL — runner, contracts, config
├── data_ingest/         # PRADEEP — openFDA client + fixtures
├── drug_normalization/  # SHARATH — RxNorm
├── graph_analytics/     # PRADEEP + SUNIL — graph + Louvain + PRR/ROR
├── ml_models/           # SHARATH — XGBoost + tuning + SHAP
├── validation/          # SHARATH — FDA enforcement ground truth
├── visualization/       # SUNIL — FastAPI + D3 dashboard
├── scalability/         # PRADEEP — benchmarks
├── user_study/          # SUNIL — survey runner
└── tests/               # each owner tests own module
```

## Modes

| Mode      | What it does                                                     |
|-----------|------------------------------------------------------------------|
| `pipeline`| Run ingest → normalize → graph → ML → validation, print summary  |
| `serve`   | Run pipeline once, then start FastAPI + D3 dashboard on `:8000`  |
| `validate`| Run pipeline + validation report                                  |
| `benchmark`| Sweep record counts, report wall-clock                          |

## `--live` flag

- **Without** `--live`: uses committed fixtures in `code/data_ingest/fixtures/`. Deterministic, fast, offline.
- **With** `--live`: hits openFDA, RxNorm, RxNav real APIs. No data persisted to disk.
