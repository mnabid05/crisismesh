from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from app.demand_training import DEMAND_OUTPUT_NAMES, DemandTrainingExample, demand_examples
from app.prediction_features import PREDICTION_FEATURE_NAMES
from app.training_data import chronological_split, read_jsonl


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def forward(
    example: DemandTrainingExample,
    hidden_weights: list[list[float]],
    hidden_bias: list[float],
    latent_weights: list[list[float]],
    latent_bias: list[float],
    output_weights: list[list[float]],
    output_bias: list[float],
) -> tuple[list[float], list[float], list[float]]:
    hidden = [
        math.tanh(
            sum(weight * value for weight, value in zip(row, example.features, strict=True)) + bias
        )
        for row, bias in zip(hidden_weights, hidden_bias, strict=True)
    ]
    latent = [
        math.tanh(sum(weight * value for weight, value in zip(row, hidden, strict=True)) + bias)
        for row, bias in zip(latent_weights, latent_bias, strict=True)
    ]
    outputs = [
        sigmoid(sum(weight * value for weight, value in zip(row, latent, strict=True)) + bias)
        for row, bias in zip(output_weights, output_bias, strict=True)
    ]
    return hidden, latent, outputs


def regression_metrics(
    examples: list[DemandTrainingExample],
    hidden_weights: list[list[float]],
    hidden_bias: list[float],
    latent_weights: list[list[float]],
    latent_bias: list[float],
    output_weights: list[list[float]],
    output_bias: list[float],
) -> dict[str, object]:
    absolute = [0.0] * len(DEMAND_OUTPUT_NAMES)
    squared = [0.0] * len(DEMAND_OUTPUT_NAMES)
    targets = [[] for _ in DEMAND_OUTPUT_NAMES]
    predictions = [[] for _ in DEMAND_OUTPUT_NAMES]
    for example in examples:
        _, _, outputs = forward(
            example,
            hidden_weights,
            hidden_bias,
            latent_weights,
            latent_bias,
            output_weights,
            output_bias,
        )
        for index, (prediction, target) in enumerate(zip(outputs, example.targets, strict=True)):
            absolute[index] += abs(prediction - target)
            squared[index] += (prediction - target) ** 2
            targets[index].append(target)
            predictions[index].append(prediction)
    size = max(1, len(examples))
    mae = [round(value / size, 6) for value in absolute]
    rmse = [round(math.sqrt(value / size), 6) for value in squared]
    r_squared: list[float] = []
    for expected, predicted in zip(targets, predictions, strict=True):
        mean = sum(expected) / max(1, len(expected))
        residual = sum((left - right) ** 2 for left, right in zip(expected, predicted, strict=True))
        total = sum((value - mean) ** 2 for value in expected)
        r_squared.append(round(1.0 - residual / total, 6) if total else 0.0)
    return {
        "mae": mae,
        "rmse": rmse,
        "rSquared": r_squared,
        "macroMae": round(sum(mae) / len(mae), 6),
    }


def train(examples: list[DemandTrainingExample], *, epochs: int, seed: int) -> dict[str, object]:
    training, validation, test = chronological_split(examples)  # type: ignore[arg-type]
    randomizer = random.Random(seed)
    hidden_size = 16
    latent_size = 10
    output_size = len(DEMAND_OUTPUT_NAMES)
    scale = 1.0 / math.sqrt(len(PREDICTION_FEATURE_NAMES))
    hidden_weights = [
        [randomizer.uniform(-scale, scale) for _ in PREDICTION_FEATURE_NAMES]
        for _ in range(hidden_size)
    ]
    hidden_bias = [0.0] * hidden_size
    latent_weights = [
        [randomizer.uniform(-0.25, 0.25) for _ in range(hidden_size)]
        for _ in range(latent_size)
    ]
    latent_bias = [0.0] * latent_size
    output_weights = [
        [randomizer.uniform(-0.2, 0.2) for _ in range(latent_size)]
        for _ in range(output_size)
    ]
    output_bias = [-1.2] * output_size
    best: tuple[
        float,
        list[list[float]],
        list[float],
        list[list[float]],
        list[float],
        list[list[float]],
        list[float],
    ] | None = None
    stale = 0

    for epoch in range(epochs):
        learning_rate = 0.032 / (1.0 + epoch * 0.055)
        indices = list(range(len(training)))
        randomizer.shuffle(indices)
        for example_index in indices:
            example = training[example_index]
            hidden, latent, outputs = forward(
                example,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
            )
            output_delta = [
                (prediction - target) * prediction * (1.0 - prediction)
                for prediction, target in zip(outputs, example.targets, strict=True)
            ]
            latent_delta = [
                (1.0 - value * value)
                * sum(
                    output_delta[output_index] * output_weights[output_index][index]
                    for output_index in range(output_size)
                )
                for index, value in enumerate(latent)
            ]
            hidden_delta = [
                (1.0 - value * value)
                * sum(
                    latent_delta[latent_index] * latent_weights[latent_index][index]
                    for latent_index in range(latent_size)
                )
                for index, value in enumerate(hidden)
            ]
            for output_index in range(output_size):
                for index in range(latent_size):
                    output_weights[output_index][index] -= (
                        learning_rate * output_delta[output_index] * latent[index]
                    )
                output_bias[output_index] -= learning_rate * output_delta[output_index]
            for latent_index in range(latent_size):
                for hidden_index in range(hidden_size):
                    latent_weights[latent_index][hidden_index] -= (
                        learning_rate * latent_delta[latent_index] * hidden[hidden_index]
                    )
                latent_bias[latent_index] -= learning_rate * latent_delta[latent_index]
            for index in range(hidden_size):
                for feature_index, feature in enumerate(example.features):
                    hidden_weights[index][feature_index] -= (
                        learning_rate * hidden_delta[index] * feature
                    )
                hidden_bias[index] -= learning_rate * hidden_delta[index]

        validation_metrics = regression_metrics(
            validation,
            hidden_weights,
            hidden_bias,
            latent_weights,
            latent_bias,
            output_weights,
            output_bias,
        )
        mean_score = float(validation_metrics["macroMae"])
        if best is None or mean_score < best[0] - 0.00001:
            best = (
                mean_score,
                [row[:] for row in hidden_weights],
                hidden_bias[:],
                [row[:] for row in latent_weights],
                latent_bias[:],
                [row[:] for row in output_weights],
                output_bias[:],
            )
            stale = 0
        else:
            stale += 1
        if stale >= 8:
            break

    assert best is not None
    (
        _,
        hidden_weights,
        hidden_bias,
        latent_weights,
        latent_bias,
        output_weights,
        output_bias,
    ) = best
    return {
        "version": "neural-demand-v3.0.0",
        "kind": "multi-output-feed-forward-regression-network",
        "windowHours": 6,
        "features": list(PREDICTION_FEATURE_NAMES),
        "outputs": list(DEMAND_OUTPUT_NAMES),
        "normalization": {
            "strategy": "bounded-domain-scaling",
            "range": [0.0, 1.0],
            "contract": "app.features and app.prediction_features",
        },
        "architecture": [len(PREDICTION_FEATURE_NAMES), hidden_size, latent_size, output_size],
        "hiddenWeights": hidden_weights,
        "hiddenBias": hidden_bias,
        "latentWeights": latent_weights,
        "latentBias": latent_bias,
        "outputWeights": output_weights,
        "outputBias": output_bias,
        "metrics": {
            "validation": regression_metrics(
                validation,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
            ),
            "test": regression_metrics(
                test,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
            ),
            "split": {"train": len(training), "validation": len(validation), "test": len(test)},
        },
        "training": {
            "seed": seed,
            "records": len(examples),
            "target": "six-hour normalized resource-demand pressure planning proxies",
            "sources": ["NOAA Storm Events", "USGS Earthquake Catalog"],
            "labelType": "documented proxy derived from recorded impact and hazard profile",
        },
        "decisionAuthority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CrisisMesh six-hour demand model")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).parents[1] / "data" / "generated" / "training-v2.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1] / "models" / "neural-demand-v3.json",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260810)
    args = parser.parse_args()
    artifact = train(demand_examples(read_jsonl(args.dataset)), epochs=args.epochs, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": artifact["version"], "metrics": artifact["metrics"]}))


if __name__ == "__main__":
    main()
