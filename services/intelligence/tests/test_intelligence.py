import unittest
from datetime import UTC, datetime

from app.allocation import allocate, haversine_km
from app.models import Incident, Resource
from app.risk import score_incident


class IntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.incident = Incident(
            id="incident-1",
            title="Flash flood",
            kind="flood",
            severity="high",
            status="active",
            latitude=29.76,
            longitude=-95.37,
            confidence=0.95,
            affected_population=80_000,
            started_at=datetime.now(UTC),
        )

    def test_risk_score_is_bounded_and_explainable(self) -> None:
        result = score_incident(self.incident)
        self.assertGreaterEqual(result["riskScore"], 70)
        self.assertLessEqual(result["riskScore"], 99)
        self.assertIn("signals", result)

    def test_haversine_identity(self) -> None:
        self.assertAlmostEqual(haversine_km(10, 20, 10, 20), 0)

    def test_allocator_prefers_capability_match(self) -> None:
        resources = [
            Resource(
                "good",
                "Swift Water",
                "rescue",
                "ready",
                10,
                30,
                -95,
                ["swift-water", "medical"],
            ),
            Resource("weak", "Supply", "logistics", "ready", 10, 30, -95, ["cargo"]),
        ]
        result = allocate(self.incident, resources)
        self.assertEqual(result[0]["resourceId"], "good")
        self.assertGreater(result[0]["suitability"], result[1]["suitability"])


if __name__ == "__main__":
    unittest.main()
