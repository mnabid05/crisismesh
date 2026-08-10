from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .prediction_features import PredictionFeatureVector

DEMAND_CATALOG: dict[str, dict[str, str | float]] = {
    "shelter_beds": {
        "label": "Shelter beds",
        "unit": "beds",
        "populationFactor": 0.18,
    },
    "medical_teams": {
        "label": "Medical teams",
        "unit": "teams",
        "populationFactor": 0.00008,
    },
    "rescue_teams": {
        "label": "Rescue teams",
        "unit": "teams",
        "populationFactor": 0.000067,
    },
    "water_liters": {
        "label": "Potable water",
        "unit": "liters",
        "populationFactor": 1.5,
    },
    "meals": {
        "label": "Prepared meals",
        "unit": "meals",
        "populationFactor": 1.5,
    },
    "transport_seats": {
        "label": "Evacuation seats",
        "unit": "seats",
        "populationFactor": 0.12,
    },
}


@dataclass(frozen=True, slots=True)
class DemandPressure:
    category: str
    label: str
    unit: str
    pressure: float
    lower_pressure: float
    upper_pressure: float


class ImmediateDemandModel:
    """Six-hour, multi-resource demand-pressure regression model."""

    def __init__(self, artifact: dict[str, Any]) -> None:
        self.artifact = artifact
        self.version = str(artifact["version"])
        self.window_hours = int(artifact["windowHours"])
        self.feature_names = tuple(str(value) for value in artifact["features"])
        self.output_names = tuple(str(value) for value in artifact["outputs"])
        self.hidden_weights = tuple(
            tuple(float(value) for value in row) for row in artifact["hiddenWeights"]
        )
        self.hidden_bias = tuple(float(value) for value in artifact["hiddenBias"])
        self.latent_weights = tuple(
            tuple(float(value) for value in row) for row in artifact["latentWeights"]
        )
        self.latent_bias = tuple(float(value) for value in artifact["latentBias"])
        self.output_weights = tuple(
            tuple(float(value) for value in row) for row in artifact["outputWeights"]
        )
        self.output_bias = tuple(float(value) for value in artifact["outputBias"])
        if len(self.hidden_weights) != len(self.hidden_bias):
            raise ValueError("hidden layer dimensions do not match")
        if any(len(row) != len(self.feature_names) for row in self.hidden_weights):
            raise ValueError("feature contract does not match hidden layer")
        if len(self.latent_weights) != len(self.latent_bias) or any(
            len(row) != len(self.hidden_bias) for row in self.latent_weights
        ):
            raise ValueError("latent layer dimensions do not match")
        if len(self.output_weights) != len(self.output_names) or any(
            len(row) != len(self.latent_bias) for row in self.output_weights
        ):
            raise ValueError("output layer dimensions do not match")
        if any(name not in DEMAND_CATALOG for name in self.output_names):
            raise ValueError("model contains an unknown demand category")

    @classmethod
    def from_file(cls, path: str | Path) -> ImmediateDemandModel:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ValueError("model artifact must be a JSON object")
        return cls(artifact)

    def predict(
        self,
        features: PredictionFeatureVector,
        *,
        confidence: float,
        adjustment: float = 0.0,
    ) -> tuple[DemandPressure, ...]:
        if features.names != self.feature_names:
            raise ValueError("feature contract does not match model artifact")
        pressures = self._forward(features.values)
        width = 0.08 + (1.0 - max(0.0, min(1.0, confidence))) * 0.22
        adjustment_weights = (0.65, 0.45, 0.55, 1.0, 0.75, 0.7)
        predictions: list[DemandPressure] = []
        for name, raw, weight in zip(
            self.output_names, pressures, adjustment_weights, strict=True
        ):
            pressure = max(0.0, min(1.0, raw + adjustment * weight))
            metadata = DEMAND_CATALOG[name]
            predictions.append(
                DemandPressure(
                    category=name,
                    label=str(metadata["label"]),
                    unit=str(metadata["unit"]),
                    pressure=round(pressure, 4),
                    lower_pressure=round(max(0.0, pressure - width), 4),
                    upper_pressure=round(min(1.0, pressure + width), 4),
                )
            )
        return tuple(predictions)

    def explain(
        self,
        features: PredictionFeatureVector,
        *,
        output_index: int,
    ) -> list[dict[str, float | str]]:
        baseline = self._forward(features.values)[output_index]
        signals: list[dict[str, float | str]] = []
        for index, name in enumerate(features.names):
            ablated = list(features.values)
            ablated[index] = 0.0
            impact = (baseline - self._forward(tuple(ablated))[output_index]) * 100
            signals.append(
                {
                    "feature": name,
                    "impact": round(impact, 2),
                    "direction": "raises" if impact >= 0 else "reduces",
                }
            )
        return sorted(signals, key=lambda item: abs(float(item["impact"])), reverse=True)[:6]

    def _forward(self, values: tuple[float, ...]) -> tuple[float, ...]:
        hidden = tuple(
            math.tanh(sum(weight * value for weight, value in zip(row, values, strict=True)) + bias)
            for row, bias in zip(self.hidden_weights, self.hidden_bias, strict=True)
        )
        latent = tuple(
            math.tanh(
                sum(weight * value for weight, value in zip(row, hidden, strict=True)) + bias
            )
            for row, bias in zip(self.latent_weights, self.latent_bias, strict=True)
        )
        return tuple(
            _sigmoid(sum(weight * value for weight, value in zip(row, latent, strict=True)) + bias)
            for row, bias in zip(self.output_weights, self.output_bias, strict=True)
        )


def estimate_quantity(category: str, population: int, pressure: float) -> int:
    factor = float(DEMAND_CATALOG[category]["populationFactor"])
    quantity = max(0.0, population * factor * pressure)
    if category in {"medical_teams", "rescue_teams"} and population > 0 and pressure >= 0.1:
        return max(1, math.ceil(quantity))
    return round(quantity)


def inventory_by_category(resources: list[dict[str, Any]]) -> dict[str, int]:
    inventory = {name: 0 for name in DEMAND_CATALOG}
    for resource in resources:
        category = str(resource.get("demandCategory") or "")
        if category not in inventory:
            continue
        try:
            available = max(0, int(float(resource.get("available", 0))))
        except (TypeError, ValueError):
            available = 0
        inventory[category] += available
    return inventory


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)
