"""Feature engineering from FaersRecord stream."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..orchestrator.contracts import FaersRecord, StandardizedDrug

_AGE_BINS = [0, 18, 40, 65, 80, 120]
_AGE_LABELS = ["0-17", "18-39", "40-64", "65-79", "80+"]


def featurize(
    records: list[FaersRecord],
    drug_map: dict[str, StandardizedDrug],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (X, y) where:
    X  = feature DataFrame
    y  = label DataFrame with columns [serious, hospitalization, death]
    """
    rows = []
    labels = []
    for rec in records:
        # --- Demographic features ---
        age = rec.patient_age if rec.patient_age is not None else -1
        sex_m = 1 if rec.patient_sex == "M" else (0 if rec.patient_sex == "F" else -1)
        age_bin = _bin_age(age)

        # --- Drug features ---
        suspect_drugs = [d.name for d in rec.drugs if d.role == "suspect"]
        n_suspect = len(suspect_drugs)
        n_concomitant = sum(1 for d in rec.drugs if d.role == "concomitant")
        n_total_drugs = len(rec.drugs)

        # --- Country ---
        is_us = 1 if rec.country == "US" else 0

        # --- Reaction features ---
        n_reactions = len(rec.reactions)

        row = {
            "age": age,
            "age_bin": age_bin,
            "sex_m": sex_m,
            "n_suspect_drugs": n_suspect,
            "n_concomitant_drugs": n_concomitant,
            "n_total_drugs": n_total_drugs,
            "n_reactions": n_reactions,
            "is_us": is_us,
        }
        rows.append(row)
        labels.append({
            "serious": int(rec.serious),
            "hospitalization": int(rec.hospitalization),
            "death": int(rec.death),
        })

    X = pd.DataFrame(rows).fillna(-1)
    y = pd.DataFrame(labels)
    return X, y


def _bin_age(age: float) -> int:
    if age < 0:
        return -1
    for i, (lo, hi) in enumerate(zip(_AGE_BINS, _AGE_BINS[1:])):
        if lo <= age < hi:
            return i
    return len(_AGE_BINS) - 2
