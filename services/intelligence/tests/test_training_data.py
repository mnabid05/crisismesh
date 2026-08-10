from __future__ import annotations

import unittest

from app.training_data import (
    chronological_split,
    noaa_hazard,
    outcome_targets,
    parse_damage,
    parse_noaa_csv,
    usgs_examples,
)


class TrainingDataTests(unittest.TestCase):
    def test_damage_suffixes_are_normalized(self) -> None:
        self.assertEqual(parse_damage("12.5K"), 12_500)
        self.assertEqual(parse_damage("2M"), 2_000_000)
        self.assertEqual(parse_damage(""), 0)

    def test_noaa_csv_builds_monotonic_horizon_targets(self) -> None:
        content = (
            "EVENT_ID,EVENT_TYPE,BEGIN_DATE_TIME,END_DATE_TIME,BEGIN_LAT,BEGIN_LON,"
            "MAGNITUDE,DEATHS_DIRECT,DEATHS_INDIRECT,INJURIES_DIRECT,INJURIES_INDIRECT,"
            "DAMAGE_PROPERTY,DAMAGE_CROPS\n"
            "42,Flash Flood,05-May-24 01:00:00,05-May-24 04:00:00,35.2,-97.4,0,0,0,6,0,2M,0\n"
        )
        examples = parse_noaa_csv(content, source_url="https://example.test/noaa.csv.gz")
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].hazard, "flood")
        self.assertLessEqual(examples[0].targets[0], examples[0].targets[1])
        self.assertLessEqual(examples[0].targets[1], examples[0].targets[2])

    def test_usgs_catalog_extracts_impact_metadata(self) -> None:
        payload = {
            "features": [
                {
                    "id": "eq-1",
                    "properties": {
                        "time": 1_714_867_200_000,
                        "mag": 6.8,
                        "sig": 900,
                        "alert": "orange",
                        "felt": 140,
                        "mmi": 7.2,
                        "tsunami": 0,
                    },
                    "geometry": {"coordinates": [-122.4, 37.8, 12.0]},
                }
            ]
        }
        examples = usgs_examples(payload)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].hazard, "earthquake")
        self.assertGreater(examples[0].targets[2], 0.9)

    def test_split_is_chronological(self) -> None:
        content = (
            "EVENT_ID,EVENT_TYPE,BEGIN_DATE_TIME,END_DATE_TIME,BEGIN_LAT,BEGIN_LON,"
            "MAGNITUDE,DEATHS_DIRECT,DEATHS_INDIRECT,INJURIES_DIRECT,INJURIES_INDIRECT,"
            "DAMAGE_PROPERTY,DAMAGE_CROPS\n"
            + "\n".join(
                f"{index},Thunderstorm Wind,0{index}-May-24 01:00:00,0{index}-May-24 02:00:00,"
                f"35.2,-97.4,60,0,0,0,0,0,0"
                for index in range(1, 7)
            )
            + "\n"
        )
        train, validation, test = chronological_split(
            parse_noaa_csv(content, source_url="https://example.test/noaa.csv.gz")
        )
        self.assertLess(train[-1].occurred_at, validation[0].occurred_at)
        self.assertLess(validation[-1].occurred_at, test[0].occurred_at)

    def test_taxonomy_and_targets_are_stable(self) -> None:
        self.assertEqual(noaa_hazard("Hurricane (Typhoon)"), "storm")
        self.assertEqual(noaa_hazard("Wildfire"), "wildfire")
        self.assertEqual(outcome_targets(False, False, 2), (0.03, 0.04, 0.05))


if __name__ == "__main__":
    unittest.main()
