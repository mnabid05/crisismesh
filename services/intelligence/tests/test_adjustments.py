import unittest

from app.adjustments import capped_environmental_adjustment, hazard_environmental_adjustment
from app.features import EnvironmentalSignals


class AdjustmentTests(unittest.TestCase):
    def test_adjustment_is_hazard_aware(self) -> None:
        wet = EnvironmentalSignals(precipitation_mm=120, humidity_percent=90)
        dry = EnvironmentalSignals(temperature_c=42, humidity_percent=15, wind_speed_kph=45)

        self.assertGreater(hazard_environmental_adjustment("flood", wet), 0)
        self.assertGreater(hazard_environmental_adjustment("wildfire", dry), 0)
        self.assertEqual(hazard_environmental_adjustment("earthquake", wet), 0)

    def test_provider_spikes_cannot_dominate_the_model(self) -> None:
        extreme = EnvironmentalSignals(
            precipitation_mm=1000,
            wind_gust_kph=500,
            cape_jkg=15000,
        )

        self.assertEqual(capped_environmental_adjustment("storm", extreme), 0.08)


if __name__ == "__main__":
    unittest.main()
