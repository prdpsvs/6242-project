"""Central config — endpoints, rate limits, defaults."""
from __future__ import annotations

import os
from pathlib import Path

# API endpoints
OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_ENFORCEMENT_URL = "https://api.fda.gov/drug/enforcement.json"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
RXNAV_INTERACTION_BASE = "https://rxnav.nlm.nih.gov/REST/interaction"

# Auth (optional). Free key from https://open.fda.gov/apis/authentication/
OPENFDA_API_KEY: str | None = os.environ.get("OPENFDA_API_KEY")

# Rate limiting
OPENFDA_MAX_CONCURRENT = 4
RXNORM_MAX_CONCURRENT = 20
HTTP_TIMEOUT_S = 30
RETRY_ATTEMPTS = 4

# Paths
PKG_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PKG_ROOT / "data_ingest" / "fixtures"
FRONTEND_DIR = PKG_ROOT / "visualization" / "frontend"

# ML
RANDOM_SEED = 42
TEST_SIZE = 0.2

# Server
HOST = "127.0.0.1"
PORT = 8000
