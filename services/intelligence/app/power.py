from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .features import EnvironmentalSignals
from .weather import TTLCache

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMETERS = "T2M,PRECTOTCORR,WS10M"


class NasaPowerClient:
    def __init__(
        self,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
        cache: TTLCache | None = None,
        today: Callable[[], date] | None = None,
    ) -> None:
        self.fetch_json = fetch_json or _fetch_json
        self.cache = cache or TTLCache(ttl_seconds=21_600)
        self.today = today or (lambda: datetime.now(UTC).date())

    def enrich(
        self, latitude: float, longitude: float, current: EnvironmentalSignals | None = None
    ) -> EnvironmentalSignals:
        signals = current or EnvironmentalSignals()
        grid_latitude = round(latitude * 2) / 2
        grid_longitude = round(longitude * 2) / 2
        end = self.today() - timedelta(days=1)
        start = end - timedelta(days=6)
        cache_key = f"nasa-power:{grid_latitude:.1f}:{grid_longitude:.1f}:{end:%Y%m%d}"
        payload = self.cache.get(cache_key)
        if payload is None:
            query = urlencode(
                {
                    "parameters": POWER_PARAMETERS,
                    "community": "AG",
                    "longitude": grid_longitude,
                    "latitude": grid_latitude,
                    "start": start.strftime("%Y%m%d"),
                    "end": end.strftime("%Y%m%d"),
                    "format": "JSON",
                    "time-standard": "UTC",
                }
            )
            payload = self.fetch_json(f"{NASA_POWER_URL}?{query}")
            self.cache.set(cache_key, payload)

        properties = _mapping(payload.get("properties"))
        parameters = _mapping(properties.get("parameter"))
        return replace(
            signals,
            power_temperature_c=_average(parameters.get("T2M"), 20.0),
            power_precipitation_mm=_average(parameters.get("PRECTOTCORR")),
            power_wind_speed_ms=_average(parameters.get("WS10M")),
            climate_source="NASA POWER daily meteorology",
        )


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "CrisisMesh/0.2 disaster-intelligence portfolio",
        },
    )
    with urlopen(request, timeout=9.0) as response:  # noqa: S310
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("NASA POWER returned a non-object response")
    return payload


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _average(value: object, default: float = 0.0) -> float:
    if not isinstance(value, dict):
        return default
    values: list[float] = []
    for item in value.values():
        try:
            number = float(item)
        except (TypeError, ValueError):
            continue
        if number > -900:
            values.append(number)
    return sum(values) / len(values) if values else default
