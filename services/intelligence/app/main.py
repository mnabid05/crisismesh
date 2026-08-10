from __future__ import annotations

import asyncio
from dataclasses import fields
from typing import Any

from fastapi import FastAPI, HTTPException

from .allocation import allocate
from .features import EnvironmentalSignals
from .models import Incident, Resource
from .risk import score_incident
from .service import NeuralIntelligenceService

app = FastAPI(
    title="CrisisMesh Intelligence",
    description="Explainable neural hazard fusion and resource allocation.",
    version="0.2.0",
    docs_url="/docs",
)
INTELLIGENCE = NeuralIntelligenceService()
ENVIRONMENT_FIELDS = {field.name for field in fields(EnvironmentalSignals)}


@app.get("/healthz")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "crisismesh-intelligence",
        "modelVersion": INTELLIGENCE.prediction_model.version,
    }


@app.get("/v1/model")
def model_metadata() -> dict[str, object]:
    return {
        "version": INTELLIGENCE.model.version,
        "kind": "feed-forward-neural-network",
        "features": INTELLIGENCE.model.feature_names,
        "trainingData": "synthetic hazard-response scenarios",
        "decisionAuthority": False,
    }


@app.get("/v2/model")
def prediction_model_metadata() -> dict[str, object]:
    artifact = INTELLIGENCE.prediction_model.artifact
    return {
        "version": INTELLIGENCE.prediction_model.version,
        "kind": artifact["kind"],
        "features": INTELLIGENCE.prediction_model.feature_names,
        "normalization": artifact["normalization"],
        "horizons": INTELLIGENCE.prediction_model.horizons,
        "metrics": artifact["metrics"],
        "training": artifact["training"],
        "decisionAuthority": False,
    }


@app.get("/v2/providers/health")
def provider_health() -> dict[str, object]:
    return {
        "providers": [
            {
                "name": "Open-Meteo",
                "role": "forecast context",
                "status": "configured",
                "timeoutSeconds": 6,
                "cacheTtlSeconds": 600,
            },
            {
                "name": "NASA POWER",
                "role": "recent climate context",
                "status": "configured",
                "timeoutSeconds": 9,
                "cacheTtlSeconds": 21600,
            },
        ],
        "note": (
            "Configured means available to the service; each prediction reports "
            "request failures independently."
        ),
    }


@app.post("/v1/risk/score")
def deterministic_score(payload: dict[str, Any]) -> dict[str, object]:
    return score_incident(Incident.from_dict(payload))


@app.post("/v1/neural/score")
async def neural_score(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        incident_payload = payload.get("incident", payload)
        if not isinstance(incident_payload, dict):
            raise ValueError("incident must be a JSON object")
        incident = Incident.from_dict(incident_payload)
        environment_payload = payload.get("environment")
        environment = None
        if isinstance(environment_payload, dict):
            environment = EnvironmentalSignals(
                **{
                    key: value
                    for key, value in environment_payload.items()
                    if key in ENVIRONMENT_FIELDS
                }
            )
        return await asyncio.to_thread(INTELLIGENCE.score, incident, environment)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v2/predictions")
async def predict_escalation(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        incident_payload = payload.get("incident", payload)
        if not isinstance(incident_payload, dict):
            raise ValueError("incident must be a JSON object")
        incident = Incident.from_dict(incident_payload)
        environment_payload = payload.get("environment")
        environment = None
        if isinstance(environment_payload, dict):
            environment = EnvironmentalSignals(
                **{
                    key: value
                    for key, value in environment_payload.items()
                    if key in ENVIRONMENT_FIELDS
                }
            )
        return await asyncio.to_thread(INTELLIGENCE.predict, incident, environment)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/allocate")
def allocate_resources(payload: dict[str, Any]) -> dict[str, object]:
    incident_payload = payload.get("incident")
    resources_payload = payload.get("resources", [])
    if not isinstance(incident_payload, dict) or not isinstance(resources_payload, list):
        raise HTTPException(status_code=422, detail="incident and resources are required")
    incident = Incident.from_dict(incident_payload)
    resources = [Resource.from_dict(item) for item in resources_payload if isinstance(item, dict)]
    return {"allocations": allocate(incident, resources), "modelVersion": "allocator-v1.0"}
