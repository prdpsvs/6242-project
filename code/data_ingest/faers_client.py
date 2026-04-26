"""openFDA FAERS client.

Two paths controlled by FaersQuery.live:
- live=False: load committed JSON fixtures from fixtures/  (dev default)
- live=True : paginated async pulls from https://api.fda.gov/drug/event.json
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..orchestrator import config
from ..orchestrator.contracts import FaersQuery, FaersRecord
from . import cleaner, normalizer


# ---------- public entrypoint ----------

def fetch(query: FaersQuery) -> list[FaersRecord]:
    """Sync entrypoint used by the orchestrator."""
    if query.live:
        raws = asyncio.run(_fetch_live(query))
    else:
        raws = _fetch_fixtures()
    records = normalizer.normalize_many(raws)
    return cleaner.clean(records)


# ---------- fixture path (dev default) ----------

def _fetch_fixtures() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted(config.FIXTURE_DIR.glob("faers_*.json")):
        with open(f, encoding="utf-8") as fh:
            payload = json.load(fh)
        out.extend(payload.get("results", []))
    if not out:
        raise FileNotFoundError(
            f"No fixtures found in {config.FIXTURE_DIR}. "
            "Run with --live or add fixture files."
        )
    return out


# ---------- live path ----------

async def _fetch_live(query: FaersQuery) -> list[dict[str, Any]]:
    search = _build_search(query)
    sem = asyncio.Semaphore(config.OPENFDA_MAX_CONCURRENT)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_S, http2=True) as client:
        # First request — also gives us total
        first = await _page(client, sem, search, skip=0, limit=query.page_size)
        total = first.get("meta", {}).get("results", {}).get("total", 0)
        results: list[dict[str, Any]] = list(first.get("results", []))
        target = min(query.max_records, total)
        # openFDA caps skip at 25_000 per query; we shard by date if needed but
        # keep simple here — most class queries stay under that.
        skips = list(range(query.page_size, min(target, 25_000), query.page_size))
        tasks = [_page(client, sem, search, skip=s, limit=query.page_size) for s in skips]
        for batch in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(batch, Exception):
                continue
            results.extend(batch.get("results", []))
            if len(results) >= target:
                break
        return results[:target]


def _build_search(query: FaersQuery) -> str:
    parts = [
        f"receivedate:[{query.date_from:%Y%m%d}+TO+{query.date_to:%Y%m%d}]"
    ]
    if query.serious_only:
        parts.append("serious:1")
    if query.drug_names:
        names = "+OR+".join(
            f"patient.drug.medicinalproduct:{n.replace(' ', '+')}"
            for n in query.drug_names
        )
        parts.append(f"({names})")
    return "+AND+".join(parts)


@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS),
       wait=wait_exponential_jitter(initial=1, max=10))
async def _page(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                search: str, skip: int, limit: int) -> dict[str, Any]:
    # Build URL manually so that `+` in the Lucene search string is NOT
    # percent-encoded to %2B by httpx (which would break openFDA queries).
    url = (
        f"{config.OPENFDA_EVENT_URL}"
        f"?search={search}&limit={limit}&skip={skip}"
    )
    if config.OPENFDA_API_KEY:
        url += f"&api_key={config.OPENFDA_API_KEY}"
    async with sem:
        r = await client.get(url)
        if r.status_code == 404:
            return {"results": []}
        r.raise_for_status()
        return r.json()
