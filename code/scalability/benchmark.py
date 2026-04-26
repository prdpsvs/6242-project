"""Scalability benchmarks: wall-clock vs record count.
Owner: Pradeep Srikakolapu
"""
from __future__ import annotations

import time
from datetime import date

from rich.console import Console
from rich.table import Table

from ..orchestrator.contracts import FaersQuery
from ..data_ingest.faers_client import fetch
from ..drug_normalization.standardizer import standardize
from ..graph_analytics.graph_builder import build
from ..graph_analytics.community import detect
from ..ml_models.features import featurize
from ..ml_models.baseline import train

console = Console()

SWEEP_SIZES = [500, 1_000, 5_000, 10_000, 25_000, 50_000]


def run_benchmark(live: bool = False):
    """Run pipeline at increasing record limits, log wall-clock per stage."""
    table = Table(title="Scalability Benchmark", show_lines=True)
    table.add_column("Max records", justify="right")
    table.add_column("Ingest (s)", justify="right")
    table.add_column("Normalize (s)", justify="right")
    table.add_column("Graph build (s)", justify="right")
    table.add_column("ML train (s)", justify="right")
    table.add_column("Total (s)", justify="right")
    table.add_column("Records fetched", justify="right")

    for target in SWEEP_SIZES:
        query = FaersQuery(
            date_from=date(2023, 1, 1),
            date_to=date(2024, 12, 31),
            max_records=target,
            live=live,
        )
        try:
            t0 = time.perf_counter()
            records = fetch(query)
            t1 = time.perf_counter()

            drug_map = standardize(records, live=live)
            t2 = time.perf_counter()

            nx_g, graph_contract = build(records, drug_map)
            t3 = time.perf_counter()

            X, y = featurize(records, drug_map)
            trained = train(X, y)
            t4 = time.perf_counter()

            table.add_row(
                str(target),
                f"{t1-t0:.2f}",
                f"{t2-t1:.2f}",
                f"{t3-t2:.2f}",
                f"{t4-t3:.2f}",
                f"{t4-t0:.2f}",
                str(len(records)),
            )
        except Exception as e:
            table.add_row(str(target), "ERR", "ERR", "ERR", "ERR", "ERR", str(e)[:30])

        if not live:
            # In fixture mode, data is the same size regardless of target — no point sweeping further
            break

    console.print(table)
