from datetime import UTC, datetime
from pathlib import Path

from app.features import EnvironmentalSignals
from app.models import Incident
from app.prediction import EscalationModel
from app.prediction_features import PREDICTION_FEATURE_NAMES, build_prediction_feature_vector

MODEL_PATH = Path(__file__).parents[1] / "models" / "neural-escalation-v2.json"


def incident() -> Incident:
    return Incident(
        id="test-event",
        title="Observed earthquake",
        kind="earthquake",
        severity="high",
        status="active",
        latitude=34.1,
        longitude=-118.2,
        confidence=0.94,
        affected_population=25000,
        started_at=datetime.now(UTC),
        metadata={"depth": 12.0, "significance": 680, "alert": "yellow"},
    )


def test_prediction_contract_and_monotonic_horizons() -> None:
    model = EscalationModel.from_file(MODEL_PATH)
    features = build_prediction_feature_vector(incident(), EnvironmentalSignals())
    predictions = model.predict(features, confidence=0.9)

    assert model.feature_names == PREDICTION_FEATURE_NAMES
    assert [item.hours for item in predictions] == [6, 24, 72]
    assert predictions[0].probability <= predictions[1].probability <= predictions[2].probability
    assert all(item.lower <= item.probability <= item.upper for item in predictions)


def test_explanations_are_bounded_and_ranked() -> None:
    model = EscalationModel.from_file(MODEL_PATH)
    features = build_prediction_feature_vector(incident(), EnvironmentalSignals())
    signals = model.explain(features)

    assert 1 <= len(signals) <= 6
    assert all(signal["direction"] in {"raises", "reduces"} for signal in signals)
    impacts = [abs(float(signal["impact"])) for signal in signals]
    assert impacts == sorted(impacts, reverse=True)
