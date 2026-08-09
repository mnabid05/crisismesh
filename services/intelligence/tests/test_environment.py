from __future__ import annotations

import unittest
from datetime import date

from app.power import NasaPowerClient
from app.weather import OpenMeteoClient, TTLCache


class EnvironmentClientTests(unittest.TestCase):
    def test_open_meteo_extracts_peak_forecast_and_uses_cache(self) -> None:
        calls: list[str] = []

        def fetch(url: str) -> dict[str, object]:
            calls.append(url)
            return {
                "current": {
                    "temperature_2m": 31.5,
                    "relative_humidity_2m": 82,
                    "precipitation": 4.2,
                    "wind_speed_10m": 36,
                    "wind_gusts_10m": 58,
                },
                "hourly": {
                    "precipitation": [1, 7.5, 3],
                    "wind_speed_10m": [28, 42, 31],
                    "wind_gusts_10m": [48, 75, 55],
                    "cape": [600, 2100, 1200],
                },
            }

        client = OpenMeteoClient(fetch_json=fetch, cache=TTLCache(ttl_seconds=30))
        first = client.enrich(29.7604, -95.3698)
        second = client.enrich(29.7604, -95.3698)

        self.assertEqual(len(calls), 1)
        self.assertEqual(first, second)
        self.assertEqual(first.precipitation_mm, 7.5)
        self.assertEqual(first.wind_gust_kph, 75)
        self.assertEqual(first.cape_jkg, 2100)
        self.assertIn("forecast_hours=12", calls[0])

    def test_nasa_power_averages_valid_daily_values(self) -> None:
        calls: list[str] = []

        def fetch(url: str) -> dict[str, object]:
            calls.append(url)
            return {
                "properties": {
                    "parameter": {
                        "T2M": {"20260801": 28, "20260802": 30},
                        "PRECTOTCORR": {"20260801": 12, "20260802": -999},
                        "WS10M": {"20260801": 8, "20260802": 12},
                    }
                }
            }

        client = NasaPowerClient(
            fetch_json=fetch,
            cache=TTLCache(ttl_seconds=30),
            today=lambda: date(2026, 8, 9),
        )
        first = client.enrich(29.76, -95.37)
        second = client.enrich(29.77, -95.38)

        self.assertEqual(len(calls), 1)
        self.assertEqual(first, second)
        self.assertEqual(first.power_temperature_c, 29)
        self.assertEqual(first.power_precipitation_mm, 12)
        self.assertEqual(first.power_wind_speed_ms, 10)
        self.assertIn("latitude=30.0", calls[0])
        self.assertIn("time-standard=UTC", calls[0])


if __name__ == "__main__":
    unittest.main()
