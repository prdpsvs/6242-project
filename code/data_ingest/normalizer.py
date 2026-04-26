"""Adapts raw openFDA event JSON into FaersRecord."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from ..orchestrator.contracts import DrugMention, FaersRecord

_ROLE_MAP = {"1": "suspect", "2": "concomitant", "3": "interacting", "4": "unknown"}
_SEX_MAP = {"1": "M", "2": "F"}

# openFDA outcome codes (patient.reaction[].reactionoutcome and patient.patient_seriousness)
_SERIOUS_FIELDS = (
    "seriousnessdeath",
    "seriousnesslifethreatening",
    "seriousnesshospitalization",
    "seriousnessdisabling",
    "seriousnesscongenitalanomali",
    "seriousnessother",
)


def _parse_date(s: str | None):
    if not s:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_one(raw: dict[str, Any]) -> FaersRecord | None:
    """Turn one openFDA result dict into a FaersRecord. Returns None on bad input."""
    sid = raw.get("safetyreportid") or raw.get("safety_report_id")
    if not sid:
        return None

    patient = raw.get("patient", {}) or {}
    age = patient.get("patientonsetage")
    try:
        age = float(age) if age is not None else None
    except (TypeError, ValueError):
        age = None

    sex = _SEX_MAP.get(str(patient.get("patientsex", "")), None)

    drugs_raw = patient.get("drug", []) or []
    drugs: list[DrugMention] = []
    for d in drugs_raw:
        name = d.get("medicinalproduct") or d.get("activesubstance", {}).get("activesubstancename")
        if not name:
            continue
        role = _ROLE_MAP.get(str(d.get("drugcharacterization", "4")), "unknown")
        drugs.append(DrugMention(name=str(name).strip().lower(), role=role))

    reactions = []
    outcomes = []
    for r in patient.get("reaction", []) or []:
        term = r.get("reactionmeddrapt")
        if term:
            reactions.append(str(term).strip())
        out = r.get("reactionoutcome")
        if out:
            outcomes.append(str(out))

    serious_flag = str(raw.get("serious", "0")) == "1"
    death = str(raw.get("seriousnessdeath", "0")) == "1"
    hosp = str(raw.get("seriousnesshospitalization", "0")) == "1"
    if not serious_flag:
        serious_flag = any(str(raw.get(f, "0")) == "1" for f in _SERIOUS_FIELDS)

    return FaersRecord(
        safety_report_id=str(sid),
        received_date=_parse_date(raw.get("receivedate") or raw.get("receiptdate")),
        patient_age=age,
        patient_sex=sex,
        country=raw.get("occurcountry") or raw.get("primarysourcecountry"),
        drugs=drugs,
        reactions=reactions,
        outcomes=outcomes,
        serious=serious_flag,
        death=death,
        hospitalization=hosp,
    )


def normalize_many(raws: Iterable[dict[str, Any]]) -> list[FaersRecord]:
    out: list[FaersRecord] = []
    for r in raws:
        rec = normalize_one(r)
        if rec is not None:
            out.append(rec)
    return out
