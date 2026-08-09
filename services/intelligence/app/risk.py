from __future__ import annotations

import math
from datetime import datetime, timezone

from .models import Incident

KIND_BASE = {
    "earthquake": 48,
    "flood": 56,
    "storm": 54,
    "wildfire": 58,
    "volcano": 52,
    "other": 38,
}

SEVERITY_DELTA = {"low": -12, "moderate": 0, "high": 14, "critical": 24}


def score_incident(incident: Incident, now: datetime | None = None) -> dict[str, object]:
    """Return a transparent 0-100 operational risk score, not a safety forecast."""
    current = now or datetime.now(timezone.utc)
    started = incident.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (current - started).total_seconds() / 3600)
    population_signal = min(18.0, math.log10(max(1, incident.affected_population)) * 3.2)
    recency_signal = max(0.0, 8.0 - min(age_hours, 96.0) / 12.0)
    confidence_signal = (incident.confidence - 0.5) * 8.0
    magnitude_signal = 0.0
    if incident.kind == "earthquake":
        magnitude_signal = max(0.0, float(incident.metadata.get("magnitude", 0) or 0) - 4.0) * 6.0

    raw = (
        KIND_BASE.get(incident.kind, KIND_BASE["other"])
        + SEVERITY_DELTA.get(incident.severity, 0)
        + population_signal
        + recency_signal
        + confidence_signal
        + magnitude_signal
    )
    score = round(max(1.0, min(99.0, raw)), 1)
    severity = "critical" if score >= 85 else "high" if score >= 70 else "moderate" if score >= 45 else "low"
    confidence = round(max(0.45, min(0.99, incident.confidence * 0.75 + 0.2)), 2)
    return {
        "riskScore": score,
        "confidence": confidence,
        "severity": severity,
        "signals": {
            "hazardBaseline": KIND_BASE.get(incident.kind, KIND_BASE["other"]),
            "population": round(population_signal, 1),
            "recency": round(recency_signal, 1),
            "sourceConfidence": round(confidence_signal, 1),
            "magnitude": round(magnitude_signal, 1),
        },
        "modelVersion": "rules-v1.0",
        "disclaimer": "Operational prioritization aid; not an official forecast or evacuation order.",
    }

