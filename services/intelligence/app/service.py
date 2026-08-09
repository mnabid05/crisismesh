from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .features import EnvironmentalSignals, build_feature_vector
from .models import Incident
from .neural import NeuralRiskModel
from .power import NasaPowerClient
from .weather import OpenMeteoClient

DEFAULT_MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-risk-v1.json"


class NeuralIntelligenceService:
    def __init__(
        self,
        model: NeuralRiskModel | None = None,
        weather: OpenMeteoClient | None = None,
        power: NasaPowerClient | None = None,
    ) -> None:
        self.model = model or NeuralRiskModel.from_file(DEFAULT_MODEL_PATH)
        self.weather = weather or OpenMeteoClient()
        self.power = power or NasaPowerClient()

    def score(
        self,
        incident: Incident,
        environment_override: EnvironmentalSignals | None = None,
    ) -> dict[str, Any]:
        environment = environment_override or EnvironmentalSignals()
        errors: list[dict[str, str]] = []
        if environment_override is None:
            try:
                environment = self.weather.enrich(
                    incident.latitude, incident.longitude, environment
                )
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append({"source": "Open-Meteo", "message": str(exc)})
            try:
                environment = self.power.enrich(
                    incident.latitude, incident.longitude, environment
                )
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append({"source": "NASA POWER", "message": str(exc)})

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
