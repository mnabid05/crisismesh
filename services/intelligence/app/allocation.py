from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from .models import Incident, Resource

REQUIRED_CAPABILITIES = {
    "flood": {"swift-water", "medical", "evacuation"},
    "storm": {"medical", "evacuation", "shelter"},
    "wildfire": {"medical", "evacuation", "reconnaissance"},
    "earthquake": {"structural", "medical", "search-and-rescue"},
    "volcano": {"evacuation", "reconnaissance", "medical"},
}


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius = 6371.0
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def allocate(incident: Incident, resources: list[Resource], limit: int = 3) -> list[dict[str, object]]:
    required = REQUIRED_CAPABILITIES.get(incident.kind, {"medical", "logistics"})
    candidates: list[tuple[float, Resource, float, list[str]]] = []
    for resource in resources:
        if resource.available <= 0 or resource.status not in {"ready", "partial"}:
            continue
        distance = haversine_km(incident.latitude, incident.longitude, resource.latitude, resource.longitude)
        matches = sorted(required.intersection(resource.capabilities))
        capability_score = len(matches) / max(1, len(required))
        distance_score = math.exp(-distance / 1800)
        availability_score = min(1.0, resource.available / 25)
        suitability = 0.52 * capability_score + 0.31 * distance_score + 0.17 * availability_score
        candidates.append((suitability, resource, distance, matches))

    candidates.sort(key=lambda item: item[0], reverse=True)
    allocations: list[dict[str, object]] = []
    created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for suitability, resource, distance, matches in candidates[:limit]:
        units = min(resource.available, max(1, round(incident.affected_population / 25_000)))
        eta = max(900, round(distance / 70 * 3600))
        allocation_id = "alloc-" + uuid.uuid5(uuid.NAMESPACE_URL, f"{incident.id}:{resource.id}:{created[:16]}").hex[:12]
        capability_text = ", ".join(matches) if matches else "general logistics coverage"
        allocations.append(
            {
                "id": allocation_id,
                "incidentId": incident.id,
                "resourceId": resource.id,
                "units": units,
                "etaSeconds": eta,
                "distanceKm": round(distance, 1),
                "suitability": round(suitability, 3),
                "rationale": f"Matched {capability_text}; {distance:.0f} km staging distance.",
                "status": "proposed",
                "createdAt": created,
            }
        )
    return allocations

