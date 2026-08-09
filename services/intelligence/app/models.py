from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def number(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class Incident:
    id: str
    title: str
    kind: str
    severity: str
    status: str
    latitude: float
    longitude: float
    confidence: float
    affected_population: int
    started_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Incident:
        started = data.get("startedAt")
        try:
            parsed = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            parsed = datetime.now(UTC)
        return cls(
            id=str(data.get("id", "unknown")),
            title=str(data.get("title", "Untitled incident")),
            kind=str(data.get("kind", "other")).lower(),
            severity=str(data.get("severity", "moderate")).lower(),
            status=str(data.get("status", "active")).lower(),
            latitude=number(data, "latitude"),
            longitude=number(data, "longitude"),
            confidence=max(0.0, min(1.0, number(data, "confidence", 0.65))),
            affected_population=max(0, int(number(data, "affectedPopulation"))),
            started_at=parsed,
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class Resource:
    id: str
    name: str
    kind: str
    status: str
    available: int
    latitude: float
    longitude: float
    capabilities: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Resource:
        return cls(
            id=str(data.get("id", "unknown")),
            name=str(data.get("name", "Unnamed resource")),
            kind=str(data.get("kind", "general")),
            status=str(data.get("status", "ready")),
            available=max(0, int(number(data, "available"))),
            latitude=number(data, "latitude"),
            longitude=number(data, "longitude"),
            capabilities=[str(item) for item in data.get("capabilities", [])],
        )
