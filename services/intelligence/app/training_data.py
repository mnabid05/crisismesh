from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .features import EnvironmentalSignals, build_feature_vector
from .models import Incident
from .prediction_features import PREDICTION_FEATURE_NAMES, extend_training_features


@dataclass(frozen=True, slots=True)
class TrainingExample:
    source: str
    event_id: str
    occurred_at: str
    hazard: str
    features: tuple[float, ...]
    targets: tuple[float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "features": list(self.features), "targets": list(self.targets)}


@dataclass(frozen=True, slots=True)
class DatasetSource:
    name: str
    url: str
    sha256: str
    records: int
    collected_at: str


def parse_noaa_csv(content: str, *, source_url: str) -> list[TrainingExample]:
    examples: list[TrainingExample] = []
    for row in csv.DictReader(io.StringIO(content)):
        example = noaa_example(row, source_url=source_url)
        if example is not None:
            examples.append(example)
    return examples


def noaa_example(row: dict[str, str], *, source_url: str) -> TrainingExample | None:
    event_id = (row.get("EVENT_ID") or "").strip()
    event_type = (row.get("EVENT_TYPE") or "").strip()
    occurred_at = _noaa_timestamp(row.get("BEGIN_DATE_TIME"))
    latitude = _number(row.get("BEGIN_LAT"))
    longitude = _number(row.get("BEGIN_LON"))
    if (
        not event_id
        or not event_type
        or occurred_at is None
        or not _valid_coordinates(latitude, longitude)
    ):
        return None

    hazard = noaa_hazard(event_type)
    magnitude = max(0.0, _number(row.get("MAGNITUDE")))
    end = _noaa_timestamp(row.get("END_DATE_TIME")) or occurred_at
    duration_hours = max(0.0, (end - occurred_at).total_seconds() / 3600.0)
    deaths = _integer(row.get("DEATHS_DIRECT")) + _integer(row.get("DEATHS_INDIRECT"))
    injuries = _integer(row.get("INJURIES_DIRECT")) + _integer(row.get("INJURIES_INDIRECT"))
    damage = parse_damage(row.get("DAMAGE_PROPERTY")) + parse_damage(row.get("DAMAGE_CROPS"))
    major_impact = deaths > 0 or injuries >= 5 or damage >= 1_000_000
    material_impact = major_impact or injuries > 0 or damage >= 100_000

    environment = historical_environment(event_type, hazard, magnitude)
    severity = historical_severity(event_type, magnitude)
    incident = Incident(
        id=f"noaa-{event_id}",
        title=event_type,
        kind=hazard,
        severity=severity,
        status="historical",
        latitude=latitude,
        longitude=longitude,
        confidence=0.9,
        affected_population=0,
        started_at=occurred_at,
        metadata={"sourceUrl": source_url},
    )
    base = build_feature_vector(incident, environment, now=occurred_at)
    return TrainingExample(
        source="NOAA Storm Events",
        event_id=event_id,
        occurred_at=occurred_at.isoformat(),
        hazard=hazard,
        features=extend_training_features(base),
        targets=outcome_targets(material_impact, major_impact, duration_hours),
    )


def usgs_examples(payload: dict[str, Any]) -> list[TrainingExample]:
    examples: list[TrainingExample] = []
    features = payload.get("features")
    if not isinstance(features, list):
        return examples
    for item in features:
        if not isinstance(item, dict):
            continue
        example = usgs_example(item)
        if example is not None:
            examples.append(example)
    return examples


def usgs_example(item: dict[str, Any]) -> TrainingExample | None:
    event_id = str(item.get("id", "")).strip()
    properties = item.get("properties")
    geometry = item.get("geometry")
    if not event_id or not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 3:
        return None
    longitude, latitude, depth = (_number(value) for value in coordinates[:3])
    timestamp = _number(properties.get("time"))
    if timestamp <= 0 or not _valid_coordinates(latitude, longitude):
        return None

    occurred_at = datetime.fromtimestamp(timestamp / 1000.0, tz=UTC)
    magnitude = max(0.0, _number(properties.get("mag")))
    significance = max(0.0, _number(properties.get("sig")))
    alert = str(properties.get("alert") or "").lower()
    felt = max(0.0, _number(properties.get("felt")))
    intensity = max(_number(properties.get("cdi")), _number(properties.get("mmi")))
    tsunami = _integer(properties.get("tsunami")) > 0
    major_impact = alert in {"orange", "red"} or tsunami or intensity >= 7 or significance >= 800
    material_impact = major_impact or intensity >= 5 or felt >= 100 or significance >= 600
    severity = "critical" if magnitude >= 7 else "high" if magnitude >= 5.5 else "moderate"
    incident = Incident(
        id=f"usgs-{event_id}",
        title=str(properties.get("title") or "Historical earthquake"),
        kind="earthquake",
        severity=severity,
        status="historical",
        latitude=latitude,
        longitude=longitude,
        confidence=0.99,
        affected_population=0,
        started_at=occurred_at,
        metadata={"magnitude": magnitude},
    )
    base = build_feature_vector(incident, EnvironmentalSignals(), now=occurred_at)
    return TrainingExample(
        source="USGS Earthquake Catalog",
        event_id=event_id,
        occurred_at=occurred_at.isoformat(),
        hazard="earthquake",
        features=extend_training_features(
            base,
            depth_km=depth,
            significance=significance,
            alert=alert,
        ),
        targets=outcome_targets(material_impact, major_impact, 0.0),
    )


def outcome_targets(
    material_impact: bool,
    major_impact: bool,
    duration_hours: float,
) -> tuple[float, float, float]:
    if not material_impact:
        return (0.03, 0.04, 0.05)
    peak = 0.96 if major_impact else 0.82
    early = peak if duration_hours <= 6 else max(0.18, peak * 0.45)
    day = peak if duration_hours <= 24 else max(early, peak * 0.72)
    return (round(early, 4), round(day, 4), round(peak, 4))


def noaa_hazard(event_type: str) -> str:
    value = event_type.lower()
    if "wildfire" in value:
        return "wildfire"
    if "flood" in value or "heavy rain" in value or "storm surge" in value:
        return "flood"
    if any(
        token in value
        for token in ("storm", "tornado", "wind", "hail", "hurricane", "lightning", "typhoon")
    ):
        return "storm"
    return "other"


def historical_severity(event_type: str, magnitude: float) -> str:
    value = event_type.lower()
    if "tornado" in value and magnitude >= 3:
        return "critical"
    if "hurricane" in value or magnitude >= 75:
        return "high"
    if any(token in value for token in ("flash flood", "wildfire", "tornado", "thunderstorm")):
        return "moderate"
    return "low"


def historical_environment(
    event_type: str,
    hazard: str,
    magnitude: float,
) -> EnvironmentalSignals:
    value = event_type.lower()
    wind = magnitude * 1.852 if "kt" in value else magnitude
    return EnvironmentalSignals(
        temperature_c=38.0 if "heat" in value else 20.0,
        precipitation_mm=45.0 if hazard == "flood" else 8.0 if hazard == "storm" else 0.0,
        wind_speed_kph=min(160.0, wind if hazard == "storm" else 0.0),
        wind_gust_kph=min(200.0, wind * 1.2 if hazard == "storm" else 0.0),
        humidity_percent=75.0 if hazard == "flood" else 35.0 if hazard == "wildfire" else 50.0,
        cape_jkg=2200.0 if hazard == "storm" else 0.0,
        power_temperature_c=20.0,
        power_precipitation_mm=20.0 if hazard == "flood" else 0.0,
        power_wind_speed_ms=min(30.0, wind / 3.6) if hazard == "storm" else 0.0,
        forecast_source="historical event attributes",
        climate_source="neutral historical baseline",
    )


def parse_damage(value: object) -> float:
    text = str(value or "").strip().upper().replace(",", "")
    if not text:
        return 0.0
    multiplier = 1.0
    if text[-1:] in {"K", "M", "B"}:
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}[text[-1]]
        text = text[:-1]
    return max(0.0, _number(text) * multiplier)


def chronological_split(
    examples: Iterable[TrainingExample],
) -> tuple[list[TrainingExample], list[TrainingExample], list[TrainingExample]]:
    ordered = sorted(examples, key=lambda item: (item.occurred_at, item.source, item.event_id))
    train_end = max(1, int(len(ordered) * 0.7))
    validation_end = max(train_end + 1, int(len(ordered) * 0.85))
    return ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:]


def write_jsonl(path: Path, examples: Iterable[TrainingExample]) -> str:
    lines = [
        json.dumps(example.to_dict(), separators=(",", ":"), sort_keys=True) for example in examples
    ]
    content = "\n".join(lines) + ("\n" if lines else "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def read_jsonl(path: Path) -> list[TrainingExample]:
    examples: list[TrainingExample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        features = tuple(float(value) for value in item["features"])
        targets = tuple(float(value) for value in item["targets"])
        if len(features) != len(PREDICTION_FEATURE_NAMES) or len(targets) != 3:
            raise ValueError("training record does not match the v2 feature contract")
        examples.append(
            TrainingExample(
                source=str(item["source"]),
                event_id=str(item["event_id"]),
                occurred_at=str(item["occurred_at"]),
                hazard=str(item["hazard"]),
                features=features,
                targets=(targets[0], targets[1], targets[2]),
            )
        )
    return examples


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _noaa_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    for pattern in ("%d-%b-%y %H:%M:%S", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _valid_coordinates(latitude: float, longitude: float) -> bool:
    return (
        -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
        and not (math.isclose(latitude, 0.0) and math.isclose(longitude, 0.0))
    )


def _number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _integer(value: object) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
