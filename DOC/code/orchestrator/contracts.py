"""Pydantic contracts: the only allowed inter-module integration surface."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ---------- data_ingest -> everyone ----------

class DrugMention(BaseModel):
    name: str
    role: Literal["suspect", "concomitant", "interacting", "unknown"] = "unknown"


class FaersRecord(BaseModel):
    safety_report_id: str
    received_date: date | None = None
    patient_age: float | None = None
    patient_sex: Literal["M", "F", "U"] | None = None
    country: str | None = None
    drugs: list[DrugMention] = Field(default_factory=list)
    reactions: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    serious: bool = False
    death: bool = False
    hospitalization: bool = False


# ---------- orchestrator -> data_ingest ----------

class FaersQuery(BaseModel):
    date_from: date
    date_to: date
    drug_names: list[str] | None = None
    serious_only: bool = False
    max_records: int = 50_000
    page_size: int = 100
    live: bool = False  # False = fixtures, True = real openFDA API


# ---------- drug_normalization -> graph + ml ----------

class StandardizedDrug(BaseModel):
    raw_name: str
    rxcui: str | None = None
    ingredient_rxcui: str | None = None
    ingredient_name: str | None = None
    confidence: float = 0.0


# ---------- graph_analytics -> visualization, ml ----------

class GraphNode(BaseModel):
    id: str           # "drug:RXCUI" or "ae:TERM"
    kind: Literal["drug", "ae"]
    label: str
    degree: int = 0
    community: int | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0
    prr: float | None = None
    ror: float | None = None


class DrugEventGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: dict = Field(default_factory=dict)


# ---------- visualization -> ml_models ----------

class PredictionRequest(BaseModel):
    drugs: list[str]
    age: float | None = None
    sex: Literal["M", "F", "U"] | None = None


class PredictionResponse(BaseModel):
    p_serious: float
    p_hospitalization: float
    p_death: float
    top_features: list[tuple[str, float]] = Field(default_factory=list)


# ---------- validation -> orchestrator ----------

class ValidationReport(BaseModel):
    auc_roc: float
    f1: float
    baseline_auc_prr: float
    signals_recovered: int
    signals_total: int
    per_drug: list[dict] = Field(default_factory=list)
    notes: str = ""
