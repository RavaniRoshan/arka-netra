from __future__ import annotations

from solaris.config import load_config
from solaris.pipeline import build_dataset
from solaris.models import train_models


def test_train_models_returns_metrics():
    config = load_config()
    dataset, _ = build_dataset(config)
    bundle = train_models(dataset, config)
    assert {"model", "precision", "recall", "f1"}.issubset(bundle.metrics.columns)
    assert len(bundle.metrics) == 3

