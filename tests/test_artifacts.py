from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from arkanetra.config import ROOT, load_config
from arkanetra.pipeline import build_dataset, make_predictions, run_mvp


def test_run_mvp_writes_evidence_artifacts():
    run_mvp()
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "reports" / "artifact_manifest.json"
    summary_path = root / "reports" / "event_summary.csv"
    assert manifest_path.exists()
    assert summary_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["prediction_rows"] > 0
    assert "synthetic" in manifest["data_mode"]
    assert "best_model" in manifest

    summary = pd.read_csv(summary_path)
    assert {"Quiet Sun replay", "M-class warning replay", "X-class critical replay"}.issubset(set(summary["scenario"]))
    assert summary["max_probability"].between(0, 1).all()


def test_run_mvp_goes_mode():
    config = load_config()
    config["data"]["mode"] = "goes_proxy"
    config["data"]["goes_source"] = "sample"
    config["data"]["periods"] = 100

    dataset, events = build_dataset(config)
    predictions, bundle = make_predictions(dataset, config, events)

    assert "goes_proxy" in predictions["data_mode"].iloc[0]
    assert predictions["flare_probability"].between(0, 1).all()
    assert predictions["anomaly_index"].between(0, 100).all()
    assert not predictions["mission_state"].isna().all()


def test_run_mvp_aditya_l1_mode():
    config = load_config()
    config["data"]["mode"] = "aditya_l1"
    config["data"]["periods"] = 100
    config["data"]["aditya_l1"]["soft_source"] = "solexs_sample"
    config["data"]["aditya_l1"]["hard_source"] = "hel1os_sample"
    config["data"]["aditya_l1"]["hel1os_energy_band"] = "25-100 keV"

    dataset, events = build_dataset(config)
    predictions, bundle = make_predictions(dataset, config, events)

    assert "aditya_l1" in predictions["data_mode"].iloc[0]
    assert predictions["flare_probability"].between(0, 1).all()
    assert predictions["anomaly_index"].between(0, 100).all()
    assert not predictions["mission_state"].isna().all()
    assert "soft_xray_flux" in predictions.columns
    assert "hard_xray_flux" in predictions.columns
