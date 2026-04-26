"""FastAPI server — bridges Python pipeline to D3 frontend."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ...orchestrator import config
from .routes import router, init_state

app = FastAPI(title="Drug Adverse Event Dashboard", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
_frontend = config.FRONTEND_DIR
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

app.include_router(router)


@app.get("/")
def root():
    index = _frontend / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "API running. See /docs for endpoints."}
