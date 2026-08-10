from __future__ import annotations

import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app


class FastApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_exposes_active_model(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["modelVersion"], "neural-escalation-v2.0.0")

    def test_neural_score_accepts_environment_override(self) -> None:
        response = self.client.post(
            "/v1/neural/score",
            json={
                "incident": {
                    "id": "integration-1",
                    "title": "Severe weather integration test",
                    "kind": "storm",
                    "severity": "high",
                    "status": "active",
                    "latitude": 29.76,
                    "longitude": -95.37,
                    "confidence": 0.95,
                    "affectedPopulation": 180000,
                    "startedAt": datetime.now(UTC).isoformat(),
                },
                "environment": {
                    "temperature_c": 32,
                    "precipitation_mm": 72,
                    "wind_speed_kph": 82,
                    "wind_gust_kph": 119,
                    "humidity_percent": 91,
                    "cape_jkg": 3100,
                    "power_temperature_c": 27,
                    "power_precipitation_mm": 31,
                    "power_wind_speed_ms": 17,
                    "forecast_source": "test forecast",
                    "climate_source": "test climate",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["modelVersion"], "neural-risk-v1.0.0")
        self.assertEqual(body["modelKind"], "feed-forward-neural-network")
        self.assertEqual(len(body["topSignals"]), 5)
        self.assertGreater(body["riskScore"], 50)

    def test_v2_prediction_returns_three_horizons(self) -> None:
        response = self.client.post(
            "/v2/predictions",
            json={
                "incident": {
                    "id": "prediction-1",
                    "title": "Observed earthquake",
                    "kind": "earthquake",
                    "severity": "high",
                    "status": "active",
                    "latitude": 34.1,
                    "longitude": -118.2,
                    "confidence": 0.94,
                    "affectedPopulation": 25000,
                    "startedAt": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "depth": 12,
                        "significance": 680,
                        "alert": "yellow",
                    },
                },
                "environment": {
                    "forecast_source": "test forecast",
                    "climate_source": "test climate",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["modelVersion"], "neural-escalation-v2.0.0")
        self.assertEqual([item["hours"] for item in body["horizons"]], [6, 24, 72])
        self.assertIn(body["trajectory"], {"rising", "steady"})
        self.assertEqual(body["confidenceLabel"], "strong coverage")
        self.assertLessEqual(
            body["horizons"][0]["probability"], body["horizons"][2]["probability"]
        )

    def test_provider_health_discloses_cache_and_timeout_contracts(self) -> None:
        response = self.client.get("/v2/providers/health")

        self.assertEqual(response.status_code, 200)
        providers = response.json()["providers"]
        self.assertEqual({item["name"] for item in providers}, {"Open-Meteo", "NASA POWER"})
        self.assertTrue(all(item["timeoutSeconds"] > 0 for item in providers))


if __name__ == "__main__":
    unittest.main()
