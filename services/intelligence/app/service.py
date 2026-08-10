from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .features import EnvironmentalSignals, build_feature_vector
from .models import Incident
from .neural import NeuralRiskModel
from .power import NasaPowerClient
from .prediction import EscalationModel
from .prediction_features import build_prediction_feature_vector
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
        errors: list[dict[str, str]] = []
        if environment_override is None:
            try:
                environment = self.weather.enrich(
                    incident.latitude, incident.longitude, environment
                )
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append({"source": "Open-Meteo", "message": str(exc)})
            try:
                environment = self.power.enrich(incident.latitude, incident.longitude, environment)
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

    def predict(
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
                environment = self.power.enrich(incident.latitude, incident.longitude, environment)
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append({"source": "NASA POWER", "message": str(exc)})

        features = build_prediction_feature_vector(incident, environment)
        provider_coverage = int(environment.forecast_source != "unavailable") + int(
            environment.climate_source != "unavailable"
        )
        confidence = min(0.98, incident.confidence * 0.72 + provider_coverage * 0.1)
        horizons = self.prediction_model.predict(features, confidence=confidence)
        return {
            "incidentId": incident.id,
            "target": "operational escalation likelihood for an already observed incident",
            "horizons": [asdict(horizon) for horizon in horizons],
            "confidence": round(max(0.35, confidence), 2),
            "topSignals": self.prediction_model.explain(features),
            "modelVersion": self.prediction_model.version,
            "modelKind": "multi-output-feed-forward-neural-network",
            "featureVector": features.as_dict(),
            "environment": asdict(environment),
            "sourceErrors": errors,
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
