from __future__ import annotations

from solaris.config import load_config
from solaris.pipeline import build_dataset, make_predictions


def test_pipeline_contract():
    config = load_config()
    config["data"]["periods"] = 240
    dataset, _ = build_dataset(config)
    required = {"timestamp", "flare_label", "split", "soft_xray_flux", "hard_xray_flux"}
    assert required.issubset(dataset.columns)
    assert set(dataset["split"].drop_duplicates()) == {"train", "validation", "test"}


def test_prediction_schema():
    config = load_config()
    dataset, _ = build_dataset(config)
    predictions, _ = make_predictions(dataset, config)
    required = {"flare_probability", "uncertainty_variance", "confidence_low", "confidence_high", "anomaly_index", "mission_state"}
    assert required.issubset(predictions.columns)
    assert predictions["flare_probability"].between(0, 1).all()
    assert predictions["anomaly_index"].between(0, 100).all()

