import unittest

from app.adjustments import hazard_environmental_adjustment
from app.features import EnvironmentalSignals


class AdjustmentTests(unittest.TestCase):
    def test_adjustment_is_hazard_aware(self) -> None:
        wet = EnvironmentalSignals(precipitation_mm=120, humidity_percent=90)
        dry = EnvironmentalSignals(temperature_c=42, humidity_percent=15, wind_speed_kph=45)

        self.assertGreater(hazard_environmental_adjustment("flood", wet), 0)
        self.assertGreater(hazard_environmental_adjustment("wildfire", dry), 0)
        self.assertEqual(hazard_environmental_adjustment("earthquake", wet), 0)


if __name__ == "__main__":
    unittest.main()
