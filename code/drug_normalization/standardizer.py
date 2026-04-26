"""Batch-standardize drug names across a list of FaersRecords.

live=False: fixture lookup
live=True : async RxNorm API calls with semaphore
"""
from __future__ import annotations

import asyncio
from cachetools import TTLCache
import httpx
from rapidfuzz import process as rfuzz

from ..orchestrator import config
from ..orchestrator.contracts import FaersRecord, StandardizedDrug
from .rxnorm_client import lookup_fixture, lookup_live, _FIXTURE_MAP

_cache: TTLCache = TTLCache(maxsize=10_000, ttl=3600)


def standardize(records: list[FaersRecord], live: bool = False) -> dict[str, StandardizedDrug]:
    """Return a map of raw_name -> StandardizedDrug for all unique drug names seen."""
    unique_names: set[str] = set()
    for r in records:
        for d in r.drugs:
            unique_names.add(d.name)

    if live:
        return asyncio.run(_standardize_live(list(unique_names)))
    return _standardize_fixtures(list(unique_names))


def _standardize_fixtures(names: list[str]) -> dict[str, StandardizedDrug]:
    result: dict[str, StandardizedDrug] = {}
    known_keys = list(_FIXTURE_MAP.keys())
    for name in names:
        if name in _cache:
            result[name] = _cache[name]
            continue
        entry = lookup_fixture(name)
        if entry:
            sd = StandardizedDrug(raw_name=name, **entry)
        else:
            # Fuzzy fallback within fixture map
            match = rfuzz.extractOne(name, known_keys, score_cutoff=70)
            if match:
                e2 = lookup_fixture(match[0])
                sd = StandardizedDrug(raw_name=name, **(e2 or {}), confidence=match[1] / 100)
            else:
                sd = StandardizedDrug(raw_name=name, confidence=0.0)
        _cache[name] = sd
        result[name] = sd
    return result


async def _standardize_live(names: list[str]) -> dict[str, StandardizedDrug]:
    result: dict[str, StandardizedDrug] = {}
    sem = asyncio.Semaphore(config.RXNORM_MAX_CONCURRENT)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_S) as client:
        tasks = {name: lookup_live(name, client, sem) for name in names if name not in _cache}
        responses = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, resp in zip(tasks.keys(), responses):
            if isinstance(resp, Exception) or resp is None:
                sd = StandardizedDrug(raw_name=name, confidence=0.0)
            else:
                sd = StandardizedDrug(raw_name=name, **resp)
            _cache[name] = sd
            result[name] = sd
        # Add cached
        for name in names:
            if name in _cache and name not in result:
                result[name] = _cache[name]
    return result
