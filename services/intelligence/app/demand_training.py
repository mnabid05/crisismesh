from __future__ import annotations

from dataclasses import dataclass

from .features import clamp
from .training_data import TrainingExample

DEMAND_OUTPUT_NAMES = (
    "shelter_beds",
    "medical_teams",
    "rescue_teams",
    "water_liters",
    "meals",
    "transport_seats",
)

# Relative need by hazard. These are transparent planning proxies, not observed
# deployments. They turn impact evidence into a multi-resource training target.
HAZARD_DEMAND_PROFILE: dict[str, tuple[float, ...]] = {
    "storm": (0.78, 0.42, 0.48, 0.72, 0.82, 0.74),
    "flood": (0.76, 0.52, 1.00, 0.94, 0.80, 0.88),
    "wildfire": (0.72, 0.66, 0.46, 0.78, 0.76, 1.00),
    "earthquake": (0.84, 0.92, 1.00, 0.82, 0.78, 0.86),
    "other": (0.50, 0.60, 0.42, 0.58, 0.56, 0.48),
}


@dataclass(frozen=True, slots=True)
class DemandTrainingExample:
    source: str
    event_id: str
    occurred_at: str
    hazard: str
    features: tuple[float, ...]
    targets: tuple[float, ...]


def demand_targets(example: TrainingExample) -> tuple[float, ...]:
    """Derive documented six-hour resource-pressure proxies from recorded impact."""

    profile = HAZARD_DEMAND_PROFILE.get(example.hazard, HAZARD_DEMAND_PROFILE["other"])
    severity_signal = example.features[0]
    six_hour_impact = example.targets[0]
    base_pressure = clamp(0.04 + six_hour_impact * 0.68 + severity_signal * 0.18)
    return tuple(
        round(clamp(0.02 + base_pressure * (0.30 + demand_weight * 0.70)), 4)
        for demand_weight in profile
    )


def demand_examples(examples: list[TrainingExample]) -> list[DemandTrainingExample]:
    return [
        DemandTrainingExample(
            source=example.source,
            event_id=example.event_id,
            occurred_at=example.occurred_at,
            hazard=example.hazard,
            features=example.features,
            targets=demand_targets(example),
        )
        for example in examples
    ]
