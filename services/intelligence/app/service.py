from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .adjustments import capped_environmental_adjustment
from .demand import ImmediateDemandModel, estimate_quantity, inventory_by_category
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
DEMAND_MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-demand-v3.json"


class NeuralIntelligenceService:
    def __init__(
        self,
        model: NeuralRiskModel | None = None,
        weather: OpenMeteoClient | None = None,
        power: NasaPowerClient | None = None,
        prediction_model: EscalationModel | None = None,
        demand_model: ImmediateDemandModel | None = None,
    ) -> None:
        self.model = model or NeuralRiskModel.from_file(DEFAULT_MODEL_PATH)
        self.weather = weather or OpenMeteoClient()
        self.power = power or NasaPowerClient()
        self.prediction_model = prediction_model or EscalationModel.from_file(PREDICTION_MODEL_PATH)
        self.demand_model = demand_model or ImmediateDemandModel.from_file(DEMAND_MODEL_PATH)

    def score(
        self,
        incident: Incident,
        environment_override: EnvironmentalSignals | None = None,
    ) -> dict[str, Any]:
        environment, errors = self._environment(incident, environment_override)

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
        environment, errors = self._environment(incident, environment_override)

        features = build_prediction_feature_vector(incident, environment)
        provider_coverage = int(environment.forecast_source != "unavailable") + int(
            environment.climate_source != "unavailable"
        )
        available_providers = [
            source
            for source in (environment.forecast_source, environment.climate_source)
            if source != "unavailable"
        ]
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
            "providerCoverage": {
                "available": len(available_providers),
                "expected": 2,
                "ratio": round(len(available_providers) / 2, 2),
                "sources": available_providers,
                "missing": [error["source"] for error in errors],
            },
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

    def demand(
        self,
        incident: Incident,
        environment_override: EnvironmentalSignals | None = None,
        resources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        environment, errors = self._environment(incident, environment_override)

        features = build_prediction_feature_vector(incident, environment)
        provider_coverage = int(environment.forecast_source != "unavailable") + int(
            environment.climate_source != "unavailable"
        )
        available_providers = [
            source
            for source in (environment.forecast_source, environment.climate_source)
            if source != "unavailable"
        ]
        confidence = min(0.98, incident.confidence * 0.72 + provider_coverage * 0.1)
        adjustment = capped_environmental_adjustment(incident.kind, environment)
        pressures = self.demand_model.predict(
            features,
            confidence=confidence,
            adjustment=adjustment,
        )
        demand: list[dict[str, Any]] = []
        for item in pressures:
            demand.append(
                {
                    "category": item.category,
                    "label": item.label,
                    "unit": item.unit,
                    "pressure": item.pressure,
                    "quantity": estimate_quantity(
                        item.category, incident.affected_population, item.pressure
                    ),
                    "lower": estimate_quantity(
                        item.category, incident.affected_population, item.lower_pressure
                    ),
                    "upper": estimate_quantity(
                        item.category, incident.affected_population, item.upper_pressure
                    ),
                }
            )

        inventory_provided = resources is not None
        inventory = inventory_by_category(resources or [])
        shortages: list[dict[str, Any]] = []
        for item in demand:
            available = inventory[item["category"]]
            shortfall = max(0, int(item["quantity"]) - available)
            quantity = max(1, int(item["quantity"]))
            coverage = min(1.0, available / quantity) if inventory_provided else 0.0
            shortages.append(
                {
                    **item,
                    "available": available if inventory_provided else None,
                    "shortfall": shortfall if inventory_provided else None,
                    "coverage": round(coverage, 3) if inventory_provided else None,
                    "urgency": (
                        _shortage_urgency(shortfall, quantity)
                        if inventory_provided
                        else "unknown"
                    ),
                }
            )
        shortages.sort(
            key=lambda item: (
                -float(item["shortfall"] or 0) / max(1, int(item["quantity"])),
                -float(item["pressure"]),
            )
        )
        priority_index = max(range(len(pressures)), key=lambda index: pressures[index].pressure)
        overall_pressure = sum(item.pressure for item in pressures) / len(pressures)
        return {
            "incidentId": incident.id,
            "target": "resource demand during the next six-hour immediate-response window",
            "windowHours": self.demand_model.window_hours,
            "demandIndex": round(overall_pressure * 100),
            "demandLevel": _demand_level(overall_pressure),
            "demand": demand,
            "shortages": shortages,
            "inventoryProvided": inventory_provided,
            "confidence": round(max(0.35, confidence), 2),
            "confidenceLabel": _confidence_label(confidence),
            "topSignals": self.demand_model.explain(features, output_index=priority_index),
            "modelVersion": self.demand_model.version,
            "modelKind": "multi-output-feed-forward-regression-network",
            "featureVector": features.as_dict(),
            "environment": asdict(environment),
            "sourceErrors": errors,
            "environmentalAdjustment": round(adjustment, 4),
            "providerCoverage": {
                "available": len(available_providers),
                "expected": 2,
                "ratio": round(len(available_providers) / 2, 2),
                "sources": available_providers,
                "missing": [error["source"] for error in errors],
            },
            "provenance": {
                "training": ["NOAA Storm Events", "USGS Earthquake Catalog"],
                "runtime": [environment.forecast_source, environment.climate_source],
            },
            "planningBasis": {
                "affectedPopulation": incident.affected_population,
                "quantityMethod": "pressure × affected population × disclosed category factor",
                "labelType": "recorded-impact planning proxy, not observed resource utilization",
            },
            "disclaimer": (
                "Experimental six-hour planning estimate. Quantities are modeled proxies, not "
                "verified needs or dispatch orders. Confirm with incident command, local "
                "authorities, and field assessments before acting."
            ),
        }

    def _environment(
        self,
        incident: Incident,
        override: EnvironmentalSignals | None,
    ) -> tuple[EnvironmentalSignals, list[dict[str, str | bool]]]:
        if override is not None:
            return override, []

        environment = EnvironmentalSignals()
        errors: list[dict[str, str | bool]] = []
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="provider") as executor:
            futures = {
                executor.submit(
                    self.weather.enrich,
                    incident.latitude,
                    incident.longitude,
                    EnvironmentalSignals(),
                ): "Open-Meteo",
                executor.submit(
                    self.power.enrich,
                    incident.latitude,
                    incident.longitude,
                    EnvironmentalSignals(),
                ): "NASA POWER",
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    result = future.result()
                except (OSError, TimeoutError, ValueError) as exc:
                    errors.append(provider_failure(source, exc))
                    continue
                if source == "Open-Meteo":
                    environment = replace(
                        environment,
                        temperature_c=result.temperature_c,
                        precipitation_mm=result.precipitation_mm,
                        wind_speed_kph=result.wind_speed_kph,
                        wind_gust_kph=result.wind_gust_kph,
                        humidity_percent=result.humidity_percent,
                        cape_jkg=result.cape_jkg,
                        forecast_source=result.forecast_source,
                    )
                else:
                    environment = replace(
                        environment,
                        power_temperature_c=result.power_temperature_c,
                        power_precipitation_mm=result.power_precipitation_mm,
                        power_wind_speed_ms=result.power_wind_speed_ms,
                        climate_source=result.climate_source,
                    )
        return environment, errors


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


def _demand_level(pressure: float) -> str:
    if pressure >= 0.65:
        return "critical"
    if pressure >= 0.42:
        return "high"
    if pressure >= 0.22:
        return "elevated"
    return "baseline"


def _shortage_urgency(shortfall: int, quantity: int) -> str:
    ratio = shortfall / max(1, quantity)
    if ratio >= 0.75:
        return "critical"
    if ratio >= 0.4:
        return "high"
    if ratio > 0:
        return "moderate"
    return "covered"
