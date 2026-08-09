from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.features import EnvironmentalSignals, build_feature_vector
from app.models import Incident
from app.neural import NeuralRiskModel

MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-risk-v1.json"
NOW = datetime(2026, 8, 9, 18, tzinfo=UTC)


def incident(**overrides: object) -> Incident:
    values: dict[str, object] = {
        "id": "signal-1",
        "title": "Test hazard",
        "kind": "storm",
        "severity": "moderate",
        "status": "active",
        "latitude": 29.7,
        "longitude": -95.3,
        "confidence": 0.82,
        "affected_population": 42_000,
        "started_at": NOW - timedelta(hours=8),
        "metadata": {},
    }
    values.update(overrides)
    return Incident(**values)  # type: ignore[arg-type]


class NeuralModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = NeuralRiskModel.from_file(MODEL_PATH)

    def test_prediction_is_deterministic_and_explainable(self) -> None:
        environment = EnvironmentalSignals(
            precipitation_mm=46,
            wind_speed_kph=68,
            wind_gust_kph=101,
            humidity_percent=86,
            cape_jkg=2200,
            power_precipitation_mm=19,
            power_wind_speed_ms=12,
        )
        features = build_feature_vector(incident(), environment, now=NOW)
        first = self.model.predict(features, confidence=0.84)
        second = self.model.predict(features, confidence=0.84)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first.risk_score, 1)
        self.assertLessEqual(first.risk_score, 99)
        self.assertEqual(len(first.top_signals), 5)
        self.assertEqual(first.model_version, "neural-risk-v1.0.0")

    def test_escalating_signals_increase_risk(self) -> None:
        calm = EnvironmentalSignals(
            precipitation_mm=1,
            wind_speed_kph=8,
            wind_gust_kph=12,
            humidity_percent=54,
            cape_jkg=80,
        )
        severe = EnvironmentalSignals(
            precipitation_mm=110,
            wind_speed_kph=106,
            wind_gust_kph=148,
            humidity_percent=95,
            cape_jkg=3900,
            power_precipitation_mm=61,
            power_wind_speed_ms=25,
        )
        calm_prediction = self.model.predict(
            build_feature_vector(incident(severity="low"), calm, now=NOW),
            confidence=0.8,
        )
        severe_prediction = self.model.predict(
            build_feature_vector(
                incident(severity="critical", affected_population=2_000_000),
                severe,
                now=NOW,
            ),
            confidence=0.92,
        )

        self.assertGreater(severe_prediction.risk_score, calm_prediction.risk_score + 25)


if __name__ == "__main__":
    unittest.main()
