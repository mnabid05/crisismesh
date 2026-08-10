from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .prediction_features import PredictionFeatureVector


@dataclass(frozen=True, slots=True)
class HorizonPrediction:
    hours: int
    probability: float
    lower: float
    upper: float
    level: str


class EscalationModel:
    """Versioned multi-horizon neural model for observed-incident escalation."""

    def __init__(self, artifact: dict[str, Any]) -> None:
        self.artifact = artifact
        self.version = str(artifact["version"])
        self.feature_names = tuple(str(value) for value in artifact["features"])
        self.horizons = tuple(int(value) for value in artifact["horizons"])
        self.hidden_weights = tuple(
            tuple(float(value) for value in row) for row in artifact["hiddenWeights"]
        )
        self.hidden_bias = tuple(float(value) for value in artifact["hiddenBias"])
        self.output_weights = tuple(
            tuple(float(value) for value in row) for row in artifact["outputWeights"]
        )
        self.output_bias = tuple(float(value) for value in artifact["outputBias"])
        self.calibration = tuple(float(value) for value in artifact["calibration"])
        if len(self.hidden_weights) != len(self.hidden_bias):
            raise ValueError("hidden layer dimensions do not match")
        if any(len(row) != len(self.feature_names) for row in self.hidden_weights):
            raise ValueError("feature contract does not match hidden layer")
        if len(self.output_weights) != len(self.horizons) or any(
            len(row) != len(self.hidden_bias) for row in self.output_weights
        ):
            raise ValueError("output layer dimensions do not match")

    @classmethod
    def from_file(cls, path: str | Path) -> EscalationModel:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ValueError("model artifact must be a JSON object")
        return cls(artifact)

    def predict(
        self,
        features: PredictionFeatureVector,
        *,
        confidence: float,
    ) -> tuple[HorizonPrediction, ...]:
        if features.names != self.feature_names:
            raise ValueError("feature contract does not match model artifact")
        probabilities = list(self._forward(features.values))
        for index in range(1, len(probabilities)):
            probabilities[index] = max(probabilities[index], probabilities[index - 1])
        width = 0.08 + (1.0 - max(0.0, min(1.0, confidence))) * 0.22
        return tuple(
            HorizonPrediction(
                hours=hours,
                probability=round(probability, 4),
                lower=round(max(0.0, probability - width), 4),
                upper=round(min(1.0, probability + width), 4),
                level=_level(probability),
            )
            for hours, probability in zip(self.horizons, probabilities, strict=True)
        )

    def explain(
        self, features: PredictionFeatureVector, horizon_index: int = 1
    ) -> list[dict[str, float | str]]:
        baseline = self._forward(features.values)[horizon_index]
        signals: list[dict[str, float | str]] = []
        for index, name in enumerate(features.names):
            ablated = list(features.values)
            ablated[index] = 0.0
            impact = (baseline - self._forward(tuple(ablated))[horizon_index]) * 100
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
        return tuple(
            _sigmoid(
                (sum(weight * value for weight, value in zip(row, hidden, strict=True)) + bias)
                / max(0.25, temperature)
            )
            for row, bias, temperature in zip(
                self.output_weights, self.output_bias, self.calibration, strict=True
            )
        )


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _level(probability: float) -> str:
    if probability >= 0.75:
        return "very high"
    if probability >= 0.5:
        return "high"
    if probability >= 0.25:
        return "watch"
    return "low"
