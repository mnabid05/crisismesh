from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .features import FeatureVector


@dataclass(frozen=True, slots=True)
class NeuralPrediction:
    risk_score: float
    probability: float
    confidence: float
    severity: str
    top_signals: tuple[dict[str, float | str], ...]
    model_version: str


class NeuralRiskModel:
    """Small feed-forward network with transparent feature-ablation explanations."""

    def __init__(self, artifact: dict[str, Any]) -> None:
        self.version = str(artifact["version"])
        self.feature_names = tuple(str(name) for name in artifact["features"])
        self.weights = tuple(
            tuple(tuple(float(value) for value in row) for row in layer)
            for layer in artifact["weights"]
        )
        self.biases = tuple(tuple(float(value) for value in layer) for layer in artifact["biases"])
        if len(self.weights) != len(self.biases):
            raise ValueError("model weights and biases must contain the same number of layers")
        previous_size = len(self.feature_names)
        for layer_weights, layer_biases in zip(self.weights, self.biases, strict=True):
            if len(layer_weights) != len(layer_biases):
                raise ValueError("each neural layer requires one bias per output unit")
            if any(len(row) != previous_size for row in layer_weights):
                raise ValueError("neural layer input width does not match previous layer")
            previous_size = len(layer_biases)
        if previous_size != 1:
            raise ValueError("risk model must contain exactly one output unit")

    @classmethod
    def from_file(cls, path: str | Path) -> NeuralRiskModel:
        with Path(path).open(encoding="utf-8") as model_file:
            artifact = json.load(model_file)
        if not isinstance(artifact, dict):
            raise ValueError("model artifact must be a JSON object")
        return cls(artifact)

    def predict(self, features: FeatureVector, confidence: float) -> NeuralPrediction:
        if features.names != self.feature_names:
            raise ValueError("feature contract does not match the model artifact")
        probability = self._forward(features.values)
        contributions = self._explain(features, probability)
        risk_score = round(max(1.0, min(99.0, probability * 100.0)), 1)
        return NeuralPrediction(
            risk_score=risk_score,
            probability=round(probability, 4),
            confidence=round(max(0.35, min(0.99, confidence)), 2),
            severity=_severity(risk_score),
            top_signals=contributions,
            model_version=self.version,
        )

    def _forward(self, inputs: tuple[float, ...]) -> float:
        values = inputs
        final_layer = len(self.weights) - 1
        for index, (layer_weights, layer_biases) in enumerate(
            zip(self.weights, self.biases, strict=True)
        ):
            values = tuple(
                sum(weight * value for weight, value in zip(row, values, strict=True)) + bias
                for row, bias in zip(layer_weights, layer_biases, strict=True)
            )
            if index == final_layer:
                values = tuple(_sigmoid(value) for value in values)
            else:
                values = tuple(max(0.0, value) for value in values)
        return values[0]

    def _explain(
        self, features: FeatureVector, prediction: float
    ) -> tuple[dict[str, float | str], ...]:
        impacts: list[dict[str, float | str]] = []
        for index, name in enumerate(features.names):
            ablated = list(features.values)
            ablated[index] = 0.0
            impact = (prediction - self._forward(tuple(ablated))) * 100.0
            impacts.append(
                {
                    "feature": name,
                    "impact": round(impact, 2),
                    "direction": "raises" if impact >= 0 else "reduces",
                }
            )
        impacts.sort(key=lambda item: abs(float(item["impact"])), reverse=True)
        return tuple(impacts[:5])


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _severity(score: float) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "moderate"
    return "low"
