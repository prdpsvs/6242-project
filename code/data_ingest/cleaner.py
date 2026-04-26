"""In-memory dedup + null cleanup for FaersRecords."""
from __future__ import annotations

from ..orchestrator.contracts import FaersRecord


def dedup(records: list[FaersRecord]) -> list[FaersRecord]:
    """Dedup by safety_report_id, preferring records with more complete data."""
    by_id: dict[str, FaersRecord] = {}
    for r in records:
        prev = by_id.get(r.safety_report_id)
        if prev is None or _completeness(r) > _completeness(prev):
            by_id[r.safety_report_id] = r
    return list(by_id.values())


def _completeness(r: FaersRecord) -> int:
    score = 0
    if r.patient_age is not None:
        score += 1
    if r.patient_sex is not None:
        score += 1
    if r.country:
        score += 1
    score += len(r.drugs)
    score += len(r.reactions)
    return score


def drop_empty(records: list[FaersRecord]) -> list[FaersRecord]:
    """Drop records with no drugs OR no reactions — useless for our analysis."""
    return [r for r in records if r.drugs and r.reactions]


def clean(records: list[FaersRecord]) -> list[FaersRecord]:
    return drop_empty(dedup(records))
