import unittest

from app.demand_training import DEMAND_OUTPUT_NAMES, demand_examples, demand_targets
from app.training_data import TrainingExample


def example(*, hazard: str, impact: float, severity: float = 0.72) -> TrainingExample:
    features = [0.0] * 21
    features[0] = severity
    return TrainingExample(
        source="provider",
        event_id="event",
        occurred_at="2025-01-01T00:00:00+00:00",
        hazard=hazard,
        features=tuple(features),
        targets=(impact, impact, impact),
    )


class DemandTrainingTests(unittest.TestCase):
    def test_six_hour_targets_cover_every_resource_category(self) -> None:
        targets = demand_targets(example(hazard="flood", impact=0.82))

        self.assertEqual(len(targets), len(DEMAND_OUTPUT_NAMES))
        self.assertEqual(len(DEMAND_OUTPUT_NAMES), 6)
        self.assertTrue(all(0 <= target <= 1 for target in targets))
        self.assertGreater(
            targets[DEMAND_OUTPUT_NAMES.index("rescue_teams")],
            targets[DEMAND_OUTPUT_NAMES.index("medical_teams")],
        )

    def test_recorded_impact_increases_every_pressure_target(self) -> None:
        low = demand_targets(example(hazard="storm", impact=0.03))
        high = demand_targets(example(hazard="storm", impact=0.96))

        self.assertTrue(all(right > left for left, right in zip(low, high, strict=True)))

    def test_conversion_preserves_chronological_metadata(self) -> None:
        original = example(hazard="earthquake", impact=0.82)
        converted = demand_examples([original])[0]

        self.assertEqual(converted.event_id, original.event_id)
        self.assertEqual(converted.occurred_at, original.occurred_at)
        self.assertEqual(converted.features, original.features)


if __name__ == "__main__":
    unittest.main()
