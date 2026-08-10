import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.demand import ImmediateDemandModel, estimate_quantity, inventory_by_category
from app.features import EnvironmentalSignals
from app.models import Incident
from app.prediction_features import PREDICTION_FEATURE_NAMES, build_prediction_feature_vector

MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-demand-v3.json"


def incident() -> Incident:
    return Incident(
        id="demand-test",
        title="Observed flood",
        kind="flood",
        severity="high",
        status="active",
        latitude=29.76,
        longitude=-95.37,
        confidence=0.95,
        affected_population=75_000,
        started_at=datetime.now(UTC),
        metadata={},
    )


class ImmediateDemandTests(unittest.TestCase):
    def test_demand_model_returns_six_resource_pressures(self) -> None:
        model = ImmediateDemandModel.from_file(MODEL_PATH)
        features = build_prediction_feature_vector(incident(), EnvironmentalSignals())
        predictions = model.predict(features, confidence=0.9)

        self.assertEqual(model.feature_names, PREDICTION_FEATURE_NAMES)
        self.assertEqual(model.window_hours, 6)
        self.assertEqual(len(predictions), 6)
        self.assertEqual({item.category for item in predictions}, set(model.output_names))
        self.assertTrue(
            all(item.lower_pressure <= item.pressure <= item.upper_pressure for item in predictions)
        )

    def test_quantities_scale_with_population_and_pressure(self) -> None:
        low = estimate_quantity("shelter_beds", 10_000, 0.2)
        high = estimate_quantity("shelter_beds", 20_000, 0.4)

        self.assertGreater(high, low)
        self.assertGreaterEqual(estimate_quantity("medical_teams", 10_000, 0.3), 1)

    def test_inventory_requires_explicit_unit_category(self) -> None:
        inventory = inventory_by_category(
            [
                {"demandCategory": "shelter_beds", "available": 480},
                {"demandCategory": "shelter_beds", "available": 20},
                {"kind": "shelter", "available": 999},
            ]
        )

        self.assertEqual(inventory["shelter_beds"], 500)
        self.assertEqual(inventory["medical_teams"], 0)

    def test_explanations_are_ranked_for_selected_resource(self) -> None:
        model = ImmediateDemandModel.from_file(MODEL_PATH)
        features = build_prediction_feature_vector(incident(), EnvironmentalSignals())
        signals = model.explain(features, output_index=2)
        impacts = [abs(float(item["impact"])) for item in signals]

        self.assertLessEqual(len(signals), 6)
        self.assertGreaterEqual(len(signals), 1)
        self.assertEqual(impacts, sorted(impacts, reverse=True))


if __name__ == "__main__":
    unittest.main()
