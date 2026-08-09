# Neural risk model card

## Summary

`neural-risk-v1.0.0` is a small feed-forward network used to prioritize incident records for an operator. It has 18 normalized inputs, one 12-unit ReLU hidden layer, and one sigmoid output. The score is constrained to 1–99 and is accompanied by feature-ablation explanations.

The model is a portfolio demonstration, not a validated forecast model. It cannot issue warnings, order evacuations, or dispatch resources.

## Inputs

The feature contract combines:

- Incident severity, provider confidence, estimated population exposure, recency, and earthquake magnitude.
- One-hot hazard identity for storms, floods, wildfires, and earthquakes.
- Open-Meteo temperature, precipitation, wind, gust, humidity, and convective available potential energy.
- NASA POWER daily temperature, corrected precipitation, and 10 m wind.
- The difference between current forecast temperature and the recent NASA POWER daily mean.

Every API input is bounded and normalized before inference. NASA POWER requests are rounded to a half-degree cell and cached for six hours. Open-Meteo requests are cached for ten minutes.

## Training

The checked-in artifact is reproducibly trained by `services/intelligence/scripts/train_neural_model.py` with a fixed seed. Training uses 2,400 synthetic hazard-response scenarios generated from explicit domain heuristics and noise. This is useful for demonstrating an end-to-end MLOps interface, but it is not a substitute for labeled disaster outcomes.

The artifact stores its feature order, architecture, activation functions, training metadata, weights, and biases in JSON. Inference uses only the Python standard library.

## Explanations

For each prediction, CrisisMesh sets one normalized feature to zero, reruns inference, and reports the change in output probability. The five largest absolute changes are returned as directional signal impacts. These are local ablation explanations, not causal claims.

## Evaluation gates

Automated tests require:

- Deterministic output for identical inputs.
- Scores bounded to 1–99.
- Five explanation signals with a pinned model version.
- A severe weather scenario scoring at least 25 points above a calm scenario.
- Provider parsing, caching, FastAPI health, and neural endpoint integration.

## Limitations and responsible use

- Population exposure is modeled when providers do not supply it.
- The training set is synthetic and may encode the assumptions in its label function.
- Forecast grids do not describe street-level conditions.
- Provider outages reduce confidence and are shown in the response.
- No score should be used without official agency guidance and qualified human review.

Before operational use, replace the synthetic dataset with governed, representative outcomes; perform calibration and subgroup evaluation; establish drift monitoring; and complete independent emergency-management validation.
