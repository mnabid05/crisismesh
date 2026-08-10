from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

from .features import EnvironmentalSignals
from .providers import fetch_provider_json

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m"
)


class TTLCache:
    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._values.get(key)
            if value is None or value[0] <= time.monotonic():
                self._values.pop(key, None)
                return None
            return value[1]

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._values[key] = (time.monotonic() + self.ttl_seconds, value)


class OpenMeteoClient:
    def __init__(
        self,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
        cache: TTLCache | None = None,
    ) -> None:
        self.fetch_json = fetch_json or _fetch_json
        self.cache = cache or TTLCache()

    def enrich(
        self, latitude: float, longitude: float, current: EnvironmentalSignals | None = None
    ) -> EnvironmentalSignals:
        signals = current or EnvironmentalSignals()
        cache_key = f"open-meteo:{latitude:.2f}:{longitude:.2f}"
        payload = self.cache.get(cache_key)
        if payload is None:
            query = urlencode(
                {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "current": OPEN_METEO_FIELDS,
                    "hourly": "precipitation,wind_speed_10m,wind_gusts_10m,cape",
                    "forecast_hours": 12,
                    "timezone": "UTC",
                }
            )
            payload = self.fetch_json(f"{OPEN_METEO_URL}?{query}")
            self.cache.set(cache_key, payload)

        current_weather = _mapping(payload.get("current"))
        hourly = _mapping(payload.get("hourly"))
        return replace(
            signals,
            temperature_c=_number(current_weather.get("temperature_2m"), 20.0),
            precipitation_mm=max(
                _number(current_weather.get("precipitation")),
                _maximum(hourly.get("precipitation")),
            ),
            wind_speed_kph=max(
                _number(current_weather.get("wind_speed_10m")),
                _maximum(hourly.get("wind_speed_10m")),
            ),
            wind_gust_kph=max(
                _number(current_weather.get("wind_gusts_10m")),
                _maximum(hourly.get("wind_gusts_10m")),
            ),
            humidity_percent=_number(current_weather.get("relative_humidity_2m"), 50.0),
            cape_jkg=_maximum(hourly.get("cape")),
            forecast_source="Open-Meteo best-match forecast",
        )


def _fetch_json(url: str) -> dict[str, Any]:
    return fetch_provider_json(url, source="Open-Meteo", timeout=6.0)


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _maximum(value: object) -> float:
    if not isinstance(value, list):
        return 0.0
    return max((_number(item) for item in value), default=0.0)
