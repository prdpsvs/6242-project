"""
Orchestrator / runner — wires all modules and exposes CLI.

Usage:
  python -m code.orchestrator.runner pipeline
  python -m code.orchestrator.runner pipeline --live --max-records 50000
  python -m code.orchestrator.runner serve
  python -m code.orchestrator.runner serve --live
  python -m code.orchestrator.runner validate --live
  python -m code.orchestrator.runner benchmark --live
"""
from __future__ import annotations

import time
from datetime import date
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sklearn.model_selection import train_test_split

from . import config
from .contracts import FaersQuery

console = Console()
app = typer.Typer(add_completion=False, help="Team 217 Drug AE Analysis Platform")


def _run_pipeline(
    live: bool,
    date_from: date,
    date_to: date,
    max_records: int,
    drug_names: Optional[list[str]],
    serious_only: bool,
    tune: bool,
) -> dict:
    """Core pipeline. Returns dict with all outputs for downstream use."""
    from ..data_ingest.faers_client import fetch
    from ..drug_normalization.standardizer import standardize
    from ..graph_analytics.graph_builder import build
    from ..graph_analytics.community import detect
    from ..ml_models.features import featurize
    from ..ml_models.baseline import train as train_baseline
    from ..ml_models.tuning import tune as tune_models
    from ..ml_models.explain import top_features
    from ..validation.evaluate import run as validate_run

    query = FaersQuery(
        date_from=date_from,
        date_to=date_to,
        drug_names=drug_names,
        serious_only=serious_only,
        max_records=max_records,
        live=live,
    )

    # 1. Ingest
    console.print("[cyan]Step 1/6:[/] Fetching FAERS records…", end=" ")
    t0 = time.perf_counter()
    records = fetch(query)
    console.print(f"[green]{len(records)} records[/] ({time.perf_counter()-t0:.1f}s)")

    # 2. Drug normalization
    console.print("[cyan]Step 2/6:[/] Normalizing drug names via RxNorm…", end=" ")
    t0 = time.perf_counter()
    drug_map = standardize(records, live=live)
    console.print(f"[green]{len(drug_map)} unique drugs[/] ({time.perf_counter()-t0:.1f}s)")

    # 3. Graph build
    console.print("[cyan]Step 3/6:[/] Building drug–AE graph…", end=" ")
    t0 = time.perf_counter()
    nx_graph, graph_contract = build(records, drug_map)
    console.print(
        f"[green]{len(graph_contract.nodes)} nodes · {len(graph_contract.edges)} edges[/] "
        f"({time.perf_counter()-t0:.1f}s)"
    )

    # 4. Community detection
    console.print("[cyan]Step 4/6:[/] Running Louvain community detection…", end=" ")
    t0 = time.perf_counter()
    graph_contract = detect(nx_graph, graph_contract)
    n_comm = graph_contract.meta.get("n_communities", "?")
    console.print(f"[green]{n_comm} communities[/] ({time.perf_counter()-t0:.1f}s)")

    # 5. ML feature engineering + training
    console.print("[cyan]Step 5/6:[/] Training ML models…", end=" ")
    t0 = time.perf_counter()
    X, y = featurize(records, drug_map)
    if tune and len(X) >= 50:
        models = tune_models(X, y)
    else:
        models = train_baseline(X, y)
    console.print(
        f"[green]AUC serious={models.aucs.get('serious', 'N/A')} "
        f"hosp={models.aucs.get('hospitalization', 'N/A')} "
        f"death={models.aucs.get('death', 'N/A')}[/] ({time.perf_counter()-t0:.1f}s)"
    )

    # 6. Validation
    console.print("[cyan]Step 6/6:[/] Running validation…", end=" ")
    t0 = time.perf_counter()
    _, X_test, _, y_test = train_test_split(X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_SEED)
    val_report = validate_run(models, graph_contract, X_test, y_test, live=live)
    console.print(
        f"[green]Signals {val_report.signals_recovered}/{val_report.signals_total}[/] "
        f"({time.perf_counter()-t0:.1f}s)"
    )

    return {
        "records": records,
        "drug_map": drug_map,
        "graph": graph_contract,
        "nx_graph": nx_graph,
        "models": models,
        "X": X, "y": y,
        "X_test": X_test, "y_test": y_test,
        "validation": val_report,
    }


# ---- CLI commands ----

@app.command()
def pipeline(
    live: bool = typer.Option(False, "--live", help="Fetch from real openFDA APIs instead of fixtures"),
    date_from: str = typer.Option("2023-01-01", help="YYYY-MM-DD"),
    date_to: str   = typer.Option("2024-12-31", help="YYYY-MM-DD"),
    max_records: int = typer.Option(50_000, help="Max FAERS records to fetch"),
    drugs: Optional[str] = typer.Option(None, help="Comma-separated drug names to filter"),
    serious_only: bool = typer.Option(False),
    tune: bool = typer.Option(False, help="Run Optuna HPO instead of default XGBoost"),
):
    """Run the full pipeline and print a summary."""
    drug_names = [d.strip() for d in drugs.split(",")] if drugs else None
    result = _run_pipeline(
        live=live,
        date_from=date.fromisoformat(date_from),
        date_to=date.fromisoformat(date_to),
        max_records=max_records,
        drug_names=drug_names,
        serious_only=serious_only,
        tune=tune,
    )
    _print_summary(result)


@app.command()
def serve(
    live: bool = typer.Option(False, "--live"),
    date_from: str = typer.Option("2023-01-01"),
    date_to: str   = typer.Option("2024-12-31"),
    max_records: int = typer.Option(20_000),
    host: str = typer.Option(config.HOST),
    port: int = typer.Option(config.PORT),
):
    """Run pipeline then launch interactive dashboard on http://host:port."""
    result = _run_pipeline(
        live=live,
        date_from=date.fromisoformat(date_from),
        date_to=date.fromisoformat(date_to),
        max_records=max_records,
        drug_names=None,
        serious_only=False,
        tune=False,
    )
    # Inject state into FastAPI routes
    from ..visualization.server.routes import init_state
    init_state(
        graph=result["graph"],
        models=result["models"],
        records=result["records"],
        drug_map=result["drug_map"],
        validation=result["validation"],
    )
    import uvicorn
    from ..visualization.server.app import app as fastapi_app
    console.print(Panel(f"[green]Dashboard running at http://{host}:{port}[/]\nPress Ctrl+C to stop."))
    uvicorn.run(fastapi_app, host=host, port=port, log_level="warning")


@app.command()
def validate(
    live: bool = typer.Option(False, "--live"),
    date_from: str = typer.Option("2023-01-01"),
    date_to: str   = typer.Option("2024-12-31"),
    max_records: int = typer.Option(50_000),
):
    """Run pipeline + print detailed validation report."""
    result = _run_pipeline(
        live=live,
        date_from=date.fromisoformat(date_from),
        date_to=date.fromisoformat(date_to),
        max_records=max_records,
        drug_names=None,
        serious_only=False,
        tune=False,
    )
    val = result["validation"]
    console.print(Panel(
        f"AUC-ROC (serious): {val.auc_roc}\n"
        f"F1 (serious):      {val.f1}\n"
        f"PRR baseline:      {val.baseline_auc_prr}\n"
        f"Signals recovered: {val.signals_recovered}/{val.signals_total}\n"
        f"Notes: {val.notes}",
        title="[cyan]Validation Report[/]",
    ))
    if val.per_drug:
        t = Table(show_lines=True)
        t.add_column("Drug")
        t.add_column("AE")
        t.add_column("Recovered")
        for s in val.per_drug:
            t.add_row(s["drug"], s["ae"], "[green]✓[/]" if s["recovered"] else "[red]✗[/]")
        console.print(t)


@app.command()
def benchmark(
    live: bool = typer.Option(False, "--live"),
):
    """Run scalability benchmarks."""
    from ..scalability.benchmark import run_benchmark
    run_benchmark(live=live)


def _print_summary(result: dict):
    g = result["graph"]
    m = result["models"]
    v = result["validation"]
    console.print(Panel(
        f"[b]Records:[/]    {len(result['records'])}\n"
        f"[b]Nodes:[/]      {len(g.nodes)} ({g.meta.get('n_drug_nodes',0)} drugs · {g.meta.get('n_ae_nodes',0)} AEs)\n"
        f"[b]Edges:[/]      {len(g.edges)}\n"
        f"[b]Communities:[/]{g.meta.get('n_communities','?')}\n"
        f"[b]AUC serious:[/] {m.aucs.get('serious','N/A')}\n"
        f"[b]AUC hosp.:[/]  {m.aucs.get('hospitalization','N/A')}\n"
        f"[b]AUC death:[/]  {m.aucs.get('death','N/A')}\n"
        f"[b]Signals:[/]    {v.signals_recovered}/{v.signals_total} recovered",
        title="[cyan]Pipeline Summary[/]",
    ))


if __name__ == "__main__":
    app()
