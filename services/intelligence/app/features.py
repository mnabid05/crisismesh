from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from .models import Incident

FEATURE_NAMES = (
    "severity_signal",
    "source_confidence",
    "population_exposure",
    "event_recency",
    "earthquake_magnitude",
    "hazard_storm",
    "hazard_flood",
    "hazard_wildfire",
    "hazard_earthquake",
    "forecast_heat",
    "forecast_precipitation",
    "forecast_wind",
    "forecast_gust",
    "forecast_humidity",
    "forecast_instability",
    "nasa_power_precipitation",
    "nasa_power_wind",
    "temperature_anomaly",
)

SEVERITY_SIGNALS = {"low": 0.18, "moderate": 0.42, "high": 0.72, "critical": 1.0}


@dataclass(slots=True)
class EnvironmentalSignals:
    """Weather observations used by the neural decision-support model."""

    temperature_c: float = 20.0
    precipitation_mm: float = 0.0
    wind_speed_kph: float = 0.0
    wind_gust_kph: float = 0.0
    humidity_percent: float = 50.0
    cape_jkg: float = 0.0
    power_temperature_c: float = 20.0
    power_precipitation_mm: float = 0.0
    power_wind_speed_ms: float = 0.0
    forecast_source: str = "unavailable"
    climate_source: str = "unavailable"


@dataclass(frozen=True, slots=True)
class FeatureVector:
    names: tuple[str, ...]
    values: tuple[float, ...]
    raw: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values, strict=True))


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def build_feature_vector(
    incident: Incident,
    environment: EnvironmentalSignals,
    now: datetime | None = None,
) -> FeatureVector:
    current = now or datetime.now(UTC)
    started = incident.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    age_hours = max(0.0, (current - started).total_seconds() / 3600)
    magnitude = float(incident.metadata.get("magnitude", 0.0) or 0.0)
    temperature_anomaly = environment.temperature_c - environment.power_temperature_c

    raw = {
        "severity_signal": SEVERITY_SIGNALS.get(incident.severity, 0.42),
        "source_confidence": incident.confidence,
        "population_exposure": float(incident.affected_population),
        "event_recency": age_hours,
        "earthquake_magnitude": magnitude,
        "hazard_storm": float(incident.kind == "storm"),
        "hazard_flood": float(incident.kind == "flood"),
        "hazard_wildfire": float(incident.kind == "wildfire"),
        "hazard_earthquake": float(incident.kind == "earthquake"),
        "forecast_heat": environment.temperature_c,
        "forecast_precipitation": environment.precipitation_mm,
        "forecast_wind": environment.wind_speed_kph,
        "forecast_gust": environment.wind_gust_kph,
        "forecast_humidity": environment.humidity_percent,
        "forecast_instability": environment.cape_jkg,
        "nasa_power_precipitation": environment.power_precipitation_mm,
        "nasa_power_wind": environment.power_wind_speed_ms,
        "temperature_anomaly": temperature_anomaly,
    }
    normalized = (
        raw["severity_signal"],
        clamp(raw["source_confidence"]),
        clamp(math.log10(max(1.0, raw["population_exposure"])) / 7.0),
        clamp(math.exp(-raw["event_recency"] / 72.0)),
        clamp((raw["earthquake_magnitude"] - 3.0) / 5.0),
        raw["hazard_storm"],
        raw["hazard_flood"],
        raw["hazard_wildfire"],
        raw["hazard_earthquake"],
        clamp(abs(raw["forecast_heat"] - 18.0) / 32.0),
        clamp(raw["forecast_precipitation"] / 120.0),
        clamp(raw["forecast_wind"] / 120.0),
        clamp(raw["forecast_gust"] / 160.0),
        clamp(abs(raw["forecast_humidity"] - 50.0) / 50.0),
        clamp(raw["forecast_instability"] / 4000.0),
        clamp(raw["nasa_power_precipitation"] / 80.0),
        clamp(raw["nasa_power_wind"] / 30.0),
        clamp((raw["temperature_anomaly"] + 15.0) / 30.0),
    )
    return FeatureVector(names=FEATURE_NAMES, values=normalized, raw=raw)
