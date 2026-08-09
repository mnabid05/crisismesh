from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .features import (
    FEATURE_NAMES,
    EnvironmentalSignals,
    FeatureVector,
    build_feature_vector,
    clamp,
)
from .models import Incident

PREDICTION_FEATURE_NAMES = FEATURE_NAMES + (
    "earthquake_depth",
    "provider_significance",
    "provider_alert",
)

ALERT_SIGNALS = {
    "": 0.0,
    "green": 0.2,
    "yellow": 0.5,
    "orange": 0.75,
    "red": 1.0,
}


@dataclass(frozen=True, slots=True)
class PredictionFeatureVector:
    names: tuple[str, ...]
    values: tuple[float, ...]
    raw: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values, strict=True))


def build_prediction_feature_vector(
    incident: Incident,
    environment: EnvironmentalSignals,
    now: datetime | None = None,
) -> PredictionFeatureVector:
    base = build_feature_vector(incident, environment, now=now)
    depth = _number(incident.metadata.get("depth"))
    significance = _number(incident.metadata.get("significance"))
    alert = ALERT_SIGNALS.get(str(incident.metadata.get("alert", "")).lower(), 0.0)
    raw = {
        **base.raw,
        "earthquake_depth": depth,
        "provider_significance": significance,
        "provider_alert": alert,
    }
    return PredictionFeatureVector(
        names=PREDICTION_FEATURE_NAMES,
        values=base.values
        + (
            clamp(depth / 700.0),
            clamp(significance / 1000.0),
            alert,
        ),
        raw=raw,
    )


def extend_training_features(
    base: FeatureVector,
    *,
    depth_km: float = 0.0,
    significance: float = 0.0,
    alert: str = "",
) -> tuple[float, ...]:
    """Extend the stable v1 contract for historical training records."""

    return base.values + (
        clamp(depth_km / 700.0),
        clamp(significance / 1000.0),
        ALERT_SIGNALS.get(alert.lower(), 0.0),
    )


def _number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
