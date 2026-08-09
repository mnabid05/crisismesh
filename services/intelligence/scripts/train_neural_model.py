from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from app.features import FEATURE_NAMES

SEED = 2048
HIDDEN_UNITS = 12


def sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def synthetic_example(generator: random.Random) -> tuple[list[float], float]:
    values = [generator.random() for _ in FEATURE_NAMES]
    hazard_index = generator.randrange(5)
    values[5:9] = [0.0, 0.0, 0.0, 0.0]
    if hazard_index < 4:
        values[5 + hazard_index] = 1.0

    severity, confidence, population, recency, magnitude = values[:5]
    storm, flood, wildfire, earthquake = values[5:9]
    heat, rain, wind, gust, humidity, instability, power_rain, power_wind, anomaly = values[9:]
    logit = (
        -4.3
        + 2.0 * severity
        + 0.45 * confidence
        + 1.15 * population
        + 0.55 * recency
        + 2.3 * magnitude * earthquake
        + 1.9 * rain * flood
        + 1.15 * rain * storm
        + 1.75 * gust * storm
        + 0.75 * instability * storm
        + 1.15 * wind * wildfire
        + 0.9 * heat * wildfire
        + 0.55 * humidity * wildfire
        + 0.65 * power_rain * flood
        + 0.55 * power_wind * storm
        + 0.45 * anomaly
    )
    probability = sigmoid(logit)
    label = min(0.99, max(0.01, probability + generator.gauss(0.0, 0.025)))
    return values, label


def train(
    sample_count: int, epochs: int
) -> tuple[list[list[float]], list[float], list[float], float]:
    generator = random.Random(SEED)
    samples = [synthetic_example(generator) for _ in range(sample_count)]
    hidden_weights = [
        [generator.uniform(-0.24, 0.24) for _ in FEATURE_NAMES]
        for _ in range(HIDDEN_UNITS)
    ]
    hidden_biases = [generator.uniform(0.0, 0.08) for _ in range(HIDDEN_UNITS)]
    output_weights = [generator.uniform(-0.2, 0.2) for _ in range(HIDDEN_UNITS)]
    output_bias = 0.0
    learning_rate = 0.035

    for _ in range(epochs):
        generator.shuffle(samples)
        for features, target in samples:
            hidden_pre = [
                sum(weight * value for weight, value in zip(row, features, strict=True)) + bias
                for row, bias in zip(hidden_weights, hidden_biases, strict=True)
            ]
            hidden = [max(0.0, value) for value in hidden_pre]
            output = sigmoid(
                sum(weight * value for weight, value in zip(output_weights, hidden, strict=True))
                + output_bias
            )
            output_delta = output - target
            previous_output_weights = output_weights[:]
            for hidden_index, hidden_value in enumerate(hidden):
                output_weights[hidden_index] -= learning_rate * output_delta * hidden_value
            output_bias -= learning_rate * output_delta

            for hidden_index, pre_activation in enumerate(hidden_pre):
                if pre_activation <= 0:
                    continue
                hidden_delta = output_delta * previous_output_weights[hidden_index]
                for feature_index, feature_value in enumerate(features):
                    hidden_weights[hidden_index][feature_index] -= (
                        learning_rate * hidden_delta * feature_value
                    )
                hidden_biases[hidden_index] -= learning_rate * hidden_delta
        learning_rate *= 0.96

    return hidden_weights, hidden_biases, output_weights, output_bias


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CrisisMesh neural risk model")
    parser.add_argument("--samples", type=int, default=2400)
    parser.add_argument("--epochs", type=int, default=28)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1] / "models" / "neural-risk-v1.json",
    )
    args = parser.parse_args()

    hidden_weights, hidden_biases, output_weights, output_bias = train(
        args.samples, args.epochs
    )
    artifact = {
        "version": "neural-risk-v1.0.0",
        "features": list(FEATURE_NAMES),
        "architecture": [len(FEATURE_NAMES), HIDDEN_UNITS, 1],
        "activation": ["relu", "sigmoid"],
        "training": {
            "seed": SEED,
            "samples": args.samples,
            "epochs": args.epochs,
            "target": "synthetic hazard-response scenarios",
        },
        "weights": [hidden_weights, [output_weights]],
        "biases": [hidden_biases, [output_bias]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {artifact['version']} to {args.output}")


if __name__ == "__main__":
    main()
