from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime

from app.features import EnvironmentalSignals
from app.models import Incident
from app.service import NeuralIntelligenceService


class WeatherStub:
    def enrich(
        self,
        _latitude: float,
        _longitude: float,
        current: EnvironmentalSignals,
    ) -> EnvironmentalSignals:
        return replace(
            current,
            temperature_c=32,
            precipitation_mm=41,
            forecast_source="weather stub",
        )


class PowerStub:
    def enrich(
        self,
        _latitude: float,
        _longitude: float,
        current: EnvironmentalSignals,
    ) -> EnvironmentalSignals:
        return replace(
            current,
            power_temperature_c=26,
            power_wind_speed_ms=11,
            climate_source="power stub",
        )


class FailingPowerStub:
    def enrich(
        self,
        _latitude: float,
        _longitude: float,
        _current: EnvironmentalSignals,
    ) -> EnvironmentalSignals:
        raise OSError("provider unavailable")


def incident() -> Incident:
    return Incident(
        id="provider-merge",
        title="Observed storm",
        kind="storm",
        severity="high",
        status="active",
        latitude=29.76,
        longitude=-95.37,
        confidence=0.9,
        affected_population=50_000,
        started_at=datetime.now(UTC),
        metadata={},
    )


class IntelligenceServiceTests(unittest.TestCase):
    def test_parallel_provider_results_are_merged(self) -> None:
        service = NeuralIntelligenceService(
            weather=WeatherStub(),  # type: ignore[arg-type]
            power=PowerStub(),  # type: ignore[arg-type]
        )

        environment, errors = service._environment(incident(), None)

        self.assertEqual(errors, [])
        self.assertEqual(environment.temperature_c, 32)
        self.assertEqual(environment.precipitation_mm, 41)
        self.assertEqual(environment.power_temperature_c, 26)
        self.assertEqual(environment.power_wind_speed_ms, 11)
        self.assertEqual(environment.forecast_source, "weather stub")
        self.assertEqual(environment.climate_source, "power stub")

    def test_one_provider_failure_preserves_the_other_result(self) -> None:
        service = NeuralIntelligenceService(
            weather=WeatherStub(),  # type: ignore[arg-type]
            power=FailingPowerStub(),  # type: ignore[arg-type]
        )

        environment, errors = service._environment(incident(), None)

        self.assertEqual(environment.forecast_source, "weather stub")
        self.assertEqual(environment.climate_source, "unavailable")
        self.assertEqual([error["source"] for error in errors], ["NASA POWER"])


if __name__ == "__main__":
    unittest.main()
