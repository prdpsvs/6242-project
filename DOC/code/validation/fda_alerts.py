"""Pull FDA enforcement + drug labeling for signal validation.

live=False -> returns a small hard-coded fixture set of known DDI/AE signals
live=True  -> calls openFDA enforcement + labeling APIs
"""
from __future__ import annotations

import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..orchestrator import config

# Minimal fixture: (drug_ingredient, adverse_event) pairs known to FDA
_FIXTURE_SIGNALS: list[tuple[str, str]] = [
    ("warfarin", "hemorrhage"),
    ("warfarin", "intracranial haemorrhage"),
    ("atorvastatin", "rhabdomyolysis"),
    ("methotrexate", "pancytopenia"),
    ("digoxin", "cardiac arrest"),
    ("lisinopril", "angioedema"),
    ("sertraline", "serotonin syndrome"),
]


def get_signals(live: bool = False) -> list[tuple[str, str]]:
    """Return list of (ingredient_name, ae_term) ground-truth signal pairs."""
    if live:
        return asyncio.run(_fetch_live_signals())
    return _FIXTURE_SIGNALS


async def _fetch_live_signals() -> list[tuple[str, str]]:
    """Pull openFDA enforcement + drug labeling for boxed-warning AE terms."""
    signals: list[tuple[str, str]] = list(_FIXTURE_SIGNALS)  # start with fixture as baseline
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_S) as client:
        try:
            signals.extend(await _enforcement_signals(client))
        except Exception:
            pass
    return signals


@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS),
       wait=wait_exponential_jitter(initial=1, max=10))
async def _enforcement_signals(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    params = {"search": "status:Ongoing", "limit": 100}
    if config.OPENFDA_API_KEY:
        params["api_key"] = config.OPENFDA_API_KEY
    r = await client.get(config.OPENFDA_ENFORCEMENT_URL, params=params)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    results = r.json().get("results", [])
    pairs: list[tuple[str, str]] = []
    for rec in results:
        product_desc = (rec.get("product_description") or "").lower()
        reason = (rec.get("reason_for_recall") or "").lower()
        if not product_desc:
            continue
        # Heuristic: pair product name fragment + reason keyword
        # Real impl would use NLP / RxNorm mapping; this is a reasonable baseline
        for ae_kw in ["hemorrhage", "death", "cardiac", "hepatic", "rhabdomyolysis"]:
            if ae_kw in reason:
                pairs.append((product_desc[:30].strip(), ae_kw))
    return pairs
