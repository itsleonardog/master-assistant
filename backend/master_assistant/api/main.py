"""FastAPI application exposing the Master Assistant API."""

from __future__ import annotations

from fastapi import FastAPI

from master_assistant.models.schemas import HealthResponse

app = FastAPI(title="Master Assistant", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return service liveness status."""
    return HealthResponse(status="ok")
