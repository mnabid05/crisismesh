from __future__ import annotations

from .features import EnvironmentalSignals


def hazard_environmental_adjustment(
    hazard: str,
    environment: EnvironmentalSignals,
) -> float:
    """Return a bounded-domain environmental modifier before the safety cap."""

    if hazard == "flood":
        return environment.precipitation_mm / 240.0
    if hazard == "storm":
        return (
            environment.wind_gust_kph / 800.0
            + environment.cape_jkg / 40_000.0
            + environment.precipitation_mm / 800.0
        )
    if hazard == "wildfire":
        heat = max(0.0, environment.temperature_c - 30.0) / 80.0
        dryness = max(0.0, 45.0 - environment.humidity_percent) / 300.0
        wind = environment.wind_speed_kph / 1000.0
        return heat + dryness + wind
    return 0.0


def capped_environmental_adjustment(
    hazard: str,
    environment: EnvironmentalSignals,
    *,
    maximum: float = 0.08,
) -> float:
    raw = hazard_environmental_adjustment(hazard, environment)
    return max(-maximum, min(maximum, raw))
