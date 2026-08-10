from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from app.prediction_features import PREDICTION_FEATURE_NAMES
from app.training_data import TrainingExample, chronological_split, read_jsonl


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def forward(
    example: TrainingExample,
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


def brier(
    examples: list[TrainingExample],
    hidden_weights: list[list[float]],
    hidden_bias: list[float],
    latent_weights: list[list[float]],
    latent_bias: list[float],
    output_weights: list[list[float]],
    output_bias: list[float],
    calibration: list[float] | None = None,
) -> list[float]:
    scores = [0.0, 0.0, 0.0]
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
            if calibration is not None:
                prediction = calibrated_probability(prediction, calibration[index])
            scores[index] += (prediction - target) ** 2
    return [round(value / max(1, len(examples)), 6) for value in scores]


def calibrated_probability(probability: float, temperature: float) -> float:
    bounded = min(1.0 - 1e-6, max(1e-6, probability))
    return sigmoid(math.log(bounded / (1.0 - bounded)) / temperature)


def calibration_temperatures(
    validation: list[TrainingExample],
    hidden_weights: list[list[float]],
    hidden_bias: list[float],
    latent_weights: list[list[float]],
    latent_bias: list[float],
    output_weights: list[list[float]],
    output_bias: list[float],
) -> list[float]:
    candidates = [0.65, 0.75, 0.85, 1.0, 1.15, 1.3, 1.5]
    temperatures: list[float] = []
    for horizon in range(3):
        best = (float("inf"), 1.0)
        for candidate in candidates:
            score = 0.0
            for example in validation:
                _, _, outputs = forward(
                    example,
                    hidden_weights,
                    hidden_bias,
                    latent_weights,
                    latent_bias,
                    output_weights,
                    output_bias,
                )
                prediction = calibrated_probability(outputs[horizon], candidate)
                score += (prediction - example.targets[horizon]) ** 2
            best = min(best, (score, candidate))
        temperatures.append(best[1])
    return temperatures


def roc_auc(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return 0.5
    ranked = sorted(zip(scores, labels, strict=True), key=lambda item: item[0])
    positive_rank_sum = sum(index for index, (_, label) in enumerate(ranked, start=1) if label)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def discrimination_metrics(
    examples: list[TrainingExample],
    hidden_weights: list[list[float]],
    hidden_bias: list[float],
    latent_weights: list[list[float]],
    latent_bias: list[float],
    output_weights: list[list[float]],
    output_bias: list[float],
    calibration: list[float],
) -> list[float]:
    labels = [[], [], []]
    scores = [[], [], []]
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
        for horizon in range(3):
            labels[horizon].append(int(example.targets[horizon] >= 0.5))
            scores[horizon].append(calibrated_probability(outputs[horizon], calibration[horizon]))
    return [round(roc_auc(labels[index], scores[index]), 6) for index in range(3)]


def train(examples: list[TrainingExample], *, epochs: int, seed: int) -> dict[str, object]:
    training, validation, test = chronological_split(examples)
    randomizer = random.Random(seed)
    hidden_size = 14
    latent_size = 8
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
    output_weights = [[randomizer.uniform(-0.2, 0.2) for _ in range(latent_size)] for _ in range(3)]
    output_bias = [-1.5, -1.3, -1.1]
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
        learning_rate = 0.035 / (1.0 + epoch * 0.06)
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
                    output_delta[horizon] * output_weights[horizon][index] for horizon in range(3)
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
            for horizon in range(3):
                for index in range(latent_size):
                    output_weights[horizon][index] -= (
                        learning_rate * output_delta[horizon] * latent[index]
                    )
                output_bias[horizon] -= learning_rate * output_delta[horizon]
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

        validation_brier = brier(
            validation,
            hidden_weights,
            hidden_bias,
            latent_weights,
            latent_bias,
            output_weights,
            output_bias,
        )
        mean_score = sum(validation_brier) / 3
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
        if stale >= 7:
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
    calibration = calibration_temperatures(
        validation,
        hidden_weights,
        hidden_bias,
        latent_weights,
        latent_bias,
        output_weights,
        output_bias,
    )
    return {
        "version": "neural-escalation-v2.0.0",
        "kind": "multi-output-feed-forward-neural-network",
        "features": list(PREDICTION_FEATURE_NAMES),
        "normalization": {
            "strategy": "bounded-domain-scaling",
            "range": [0.0, 1.0],
            "contract": "app.features and app.prediction_features",
        },
        "horizons": [6, 24, 72],
        "hiddenWeights": hidden_weights,
        "hiddenBias": hidden_bias,
        "latentWeights": latent_weights,
        "latentBias": latent_bias,
        "outputWeights": output_weights,
        "outputBias": output_bias,
        "calibration": calibration,
        "metrics": {
            "validationBrier": brier(
                validation,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
                calibration,
            ),
            "testBrier": brier(
                test,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
                calibration,
            ),
            "testRocAuc": discrimination_metrics(
                test,
                hidden_weights,
                hidden_bias,
                latent_weights,
                latent_bias,
                output_weights,
                output_bias,
                calibration,
            ),
            "split": {"train": len(training), "validation": len(validation), "test": len(test)},
        },
        "training": {
            "seed": seed,
            "records": len(examples),
            "target": "operational escalation proxy for an already observed incident",
            "sources": ["NOAA Storm Events", "USGS Earthquake Catalog"],
        },
        "decisionAuthority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CrisisMesh escalation model")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).parents[1] / "data" / "generated" / "training-v2.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1] / "models" / "neural-escalation-v2.json",
    )
    parser.add_argument("--epochs", type=int, default=45)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()
    artifact = train(read_jsonl(args.dataset), epochs=args.epochs, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": artifact["version"], "metrics": artifact["metrics"]}))


if __name__ == "__main__":
    main()
