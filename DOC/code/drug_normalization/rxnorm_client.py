"""RxNorm REST API client.

live=True  -> calls https://rxnav.nlm.nih.gov/REST
live=False -> returns stub RxCUI values from a small in-fixture dict
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..orchestrator import config

# Minimal fixture map: lowercase drug name -> (rxcui, ingredient_rxcui, ingredient_name)
_FIXTURE_MAP: dict[str, tuple[str, str, str]] = {
    "warfarin":        ("202421", "11289",  "warfarin"),
    "aspirin":         ("1191",   "1191",   "aspirin"),
    "amiodarone":      ("703",    "703",    "amiodarone"),
    "metformin":       ("6809",   "6809",   "metformin"),
    "atorvastatin":    ("83367",  "83367",  "atorvastatin"),
    "clarithromycin":  ("21212",  "21212",  "clarithromycin"),
    "lisinopril":      ("29046",  "29046",  "lisinopril"),
    "spironolactone":  ("9997",   "9997",   "spironolactone"),
    "digoxin":         ("3407",   "3407",   "digoxin"),
    "furosemide":      ("4603",   "4603",   "furosemide"),
    "sertraline":      ("36437",  "36437",  "sertraline"),
    "fluconazole":     ("4450",   "4450",   "fluconazole"),
    "methotrexate":    ("703",    "7821",   "methotrexate"),
    "gemfibrozil":     ("4462",   "4462",   "gemfibrozil"),
    "trimethoprim":    ("10829",  "10829",  "trimethoprim"),
    "ibuprofen":       ("5640",   "5640",   "ibuprofen"),
    "omeprazole":      ("7646",   "7646",   "omeprazole"),
    "tramadol":        ("41493",  "41493",  "tramadol"),
}


def lookup_fixture(name: str) -> dict[str, Any] | None:
    key = name.strip().lower()
    entry = _FIXTURE_MAP.get(key)
    if entry:
        return {"rxcui": entry[0], "ingredient_rxcui": entry[1], "ingredient_name": entry[2], "confidence": 1.0}
    # Try prefix match
    for k, v in _FIXTURE_MAP.items():
        if k.startswith(key[:5]) if len(key) >= 5 else key == k:
            return {"rxcui": v[0], "ingredient_rxcui": v[1], "ingredient_name": v[2], "confidence": 0.7}
    return None


async def lookup_live(name: str, client: httpx.AsyncClient, sem: asyncio.Semaphore) -> dict[str, Any] | None:
    """Call RxNorm /rxcui endpoint for a drug name."""
    url = f"{config.RXNORM_BASE}/rxcui.json"
    async with sem:
        try:
            r = await client.get(url, params={"name": name, "search": "1"})
            r.raise_for_status()
            data = r.json()
            rxcui = data.get("idGroup", {}).get("rxnormId", [None])[0]
            if not rxcui:
                return None
            # Get ingredient — called WITHOUT re-acquiring sem (already held above)
            ingr = await _get_ingredient(client, rxcui)
            return {
                "rxcui": rxcui,
                "ingredient_rxcui": ingr[0] if ingr else rxcui,
                "ingredient_name": ingr[1] if ingr else name.lower(),
                "confidence": 1.0,
            }
        except Exception:
            return None


@retry(stop=stop_after_attempt(config.RETRY_ATTEMPTS),
       wait=wait_exponential_jitter(initial=1, max=8))
async def _get_ingredient(client: httpx.AsyncClient,
                          rxcui: str) -> tuple[str, str] | None:
    # Semaphore is already held by the caller (lookup_live); do NOT re-acquire.
    url = f"{config.RXNORM_BASE}/rxcui/{rxcui}/related.json"
    r = await client.get(url, params={"tty": "IN"})
    r.raise_for_status()
    data = r.json()
    concepts = (
        data.get("relatedGroup", {})
        .get("conceptGroup", [{}])[0]
        .get("conceptProperties", [])
    )
    if concepts:
        c = concepts[0]
        return c.get("rxcui"), c.get("name", "").lower()
        return None
