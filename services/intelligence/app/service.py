from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adjustments import capped_environmental_adjustment
from .features import EnvironmentalSignals, build_feature_vector
from .models import Incident
from .neural import NeuralRiskModel
from .power import NasaPowerClient
from .prediction import EscalationModel
from .prediction_features import build_prediction_feature_vector
from .providers import provider_failure
from .weather import OpenMeteoClient

DEFAULT_MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-risk-v1.json"
PREDICTION_MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-escalation-v2.json"


class NeuralIntelligenceService:
    def __init__(
        self,
        model: NeuralRiskModel | None = None,
        weather: OpenMeteoClient | None = None,
        power: NasaPowerClient | None = None,
        prediction_model: EscalationModel | None = None,
    ) -> None:
        self.model = model or NeuralRiskModel.from_file(DEFAULT_MODEL_PATH)
        self.weather = weather or OpenMeteoClient()
        self.power = power or NasaPowerClient()
        self.prediction_model = prediction_model or EscalationModel.from_file(PREDICTION_MODEL_PATH)

    def score(
        self,
        incident: Incident,
        environment_override: EnvironmentalSignals | None = None,
    ) -> dict[str, Any]:
        environment = environment_override or EnvironmentalSignals()
        errors: list[dict[str, str | bool]] = []
        if environment_override is None:
            try:
                environment = self.weather.enrich(
                    incident.latitude, incident.longitude, environment
                )
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append(provider_failure("Open-Meteo", exc))
            try:
                environment = self.power.enrich(incident.latitude, incident.longitude, environment)
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append(provider_failure("NASA POWER", exc))

        features = build_feature_vector(incident, environment)
        provider_coverage = int(environment.forecast_source != "unavailable") + int(
            environment.climate_source != "unavailable"
        )
        confidence = incident.confidence * 0.72 + provider_coverage * 0.1
        prediction = self.model.predict(features, confidence=confidence)
        return {
            "riskScore": prediction.risk_score,
            "probability": prediction.probability,
            "confidence": prediction.confidence,
            "severity": prediction.severity,
            "topSignals": list(prediction.top_signals),
            "modelVersion": prediction.model_version,
            "modelKind": "feed-forward-neural-network",
            "featureVector": features.as_dict(),
            "rawSignals": features.raw,
            "environment": asdict(environment),
            "sourceErrors": errors,
            "disclaimer": (
                "Experimental operational prioritization aid trained on synthetic scenarios; "
                "not an official forecast, warning, or evacuation order."
            ),
        }

    def predict(
        self,
        incident: Incident,
        environment_override: EnvironmentalSignals | None = None,
    ) -> dict[str, Any]:
        environment = environment_override or EnvironmentalSignals()
        errors: list[dict[str, str | bool]] = []
        if environment_override is None:
            try:
                environment = self.weather.enrich(
                    incident.latitude, incident.longitude, environment
                )
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append(provider_failure("Open-Meteo", exc))
            try:
                environment = self.power.enrich(incident.latitude, incident.longitude, environment)
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append(provider_failure("NASA POWER", exc))

        features = build_prediction_feature_vector(incident, environment)
        provider_coverage = int(environment.forecast_source != "unavailable") + int(
            environment.climate_source != "unavailable"
        )
        confidence = min(0.98, incident.confidence * 0.72 + provider_coverage * 0.1)
        horizons = self.prediction_model.predict(features, confidence=confidence)
        adjustment = capped_environmental_adjustment(incident.kind, environment)
        adjusted_horizons: list[dict[str, Any]] = []
        previous = 0.0
        for horizon, weight in zip(horizons, (0.65, 1.0, 0.5), strict=True):
            item = asdict(horizon)
            delta = adjustment * weight
            probability = max(previous, min(1.0, horizon.probability + delta))
            item["probability"] = round(probability, 4)
            item["lower"] = round(max(0.0, min(probability, horizon.lower + delta)), 4)
            item["upper"] = round(min(1.0, max(probability, horizon.upper + delta)), 4)
            item["level"] = _prediction_level(probability)
            adjusted_horizons.append(item)
            previous = probability
        spread = adjusted_horizons[-1]["probability"] - adjusted_horizons[0]["probability"]
        return {
            "incidentId": incident.id,
            "target": "operational escalation likelihood for an already observed incident",
            "horizons": adjusted_horizons,
            "confidence": round(max(0.35, confidence), 2),
            "confidenceLabel": _confidence_label(confidence),
            "trajectory": "rising" if spread >= 0.08 else "steady",
            "topSignals": self.prediction_model.explain(features),
            "modelVersion": self.prediction_model.version,
            "modelKind": "multi-output-feed-forward-neural-network",
            "featureVector": features.as_dict(),
            "environment": asdict(environment),
            "sourceErrors": errors,
            "environmentalAdjustment": round(adjustment, 4),
            "provenance": {
                "training": ["NOAA Storm Events 2025", "USGS Earthquake Catalog 2025"],
                "runtime": [environment.forecast_source, environment.climate_source],
            },
            "disclaimer": (
                "Experimental escalation aid for already observed incidents. It is not an "
                "official forecast, warning, evacuation order, or prediction that a disaster "
                "will occur. Follow local authorities and linked official sources."
            ),
        }


def _prediction_level(probability: float) -> str:
    if probability >= 0.75:
        return "very high"
    if probability >= 0.5:
        return "high"
    if probability >= 0.25:
        return "watch"
    return "low"


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "strong coverage"
    if confidence >= 0.65:
        return "moderate coverage"
    return "limited coverage"
