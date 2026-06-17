from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from arkanetra.data.goes import (
    _add_quality_flags,
    _flare_class_to_severity,
    _resample_to_cadence,
    _scenario_for_class,
    load_goes_xrs,
)


def test_load_goes_xrs_validates_columns(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_goes_xrs(bad)


def test_load_goes_xrs_utc_normalized(tmp_path: Path):
    good = tmp_path / "good.csv"
    good.write_text(
        "timestamp,soft_xray_flux\n" "2024-01-01T00:00:00,1.0e-6\n" "2024-01-01T00:05:00,2.0e-6\n",
        encoding="utf-8",
    )
    frame = load_goes_xrs(good)
    assert frame["timestamp"].dt.tz is not None
    assert list(frame.columns) == ["timestamp", "soft_xray_flux", "data_quality"]
    assert len(frame) == 2


def test_load_goes_xrs_sorts(tmp_path: Path):
    unsorted = tmp_path / "unsorted.csv"
    unsorted.write_text(
        "timestamp,soft_xray_flux\n" "2024-01-01T00:05:00,2.0e-6\n" "2024-01-01T00:00:00,1.0e-6\n",
        encoding="utf-8",
    )
    frame = load_goes_xrs(unsorted)
    assert frame["timestamp"].iloc[0] < frame["timestamp"].iloc[1]


def test_quality_flags():
    import numpy as np
    frame = pd.DataFrame({"soft_xray_flux": [1.0e-6, -1.0, np.nan, 1.0e-12, 5.0e-2]})
    flagged = _add_quality_flags(frame)
    assert flagged["data_quality"].tolist() == ["ok", "invalid", "invalid", "stale", "suspect_high"]


def test_resample_to_cadence():
    timestamps = pd.date_range("2024-01-01T00:00:00Z", periods=10, freq="1min", tz="UTC")
    frame = pd.DataFrame({"timestamp": timestamps, "soft_xray_flux": range(10)})
    resampled = _resample_to_cadence(frame, 5)
    assert len(resampled) == 2
    assert resampled["timestamp"].iloc[0] == pd.Timestamp("2024-01-01T00:00:00Z")
    assert resampled["timestamp"].iloc[1] == pd.Timestamp("2024-01-01T00:05:00Z")


def test_build_goes_replay_matches_contract():
    from arkanetra.config import load_config
    from arkanetra.data.goes import build_goes_replay

    config = load_config()
    config["data"]["mode"] = "goes_proxy"
    config["data"]["goes_source"] = "sample"

    frame, events = build_goes_replay(config)

    assert "timestamp" in frame.columns
    assert "soft_xray_flux" in frame.columns
    assert "hard_xray_flux" in frame.columns
    assert "soft_source" in frame.columns
    assert "hard_source" in frame.columns
    assert frame["soft_source"].iloc[0] == "GOES_XRS_SAMPLE"
    if frame["hard_xray_flux"].sum() > 0:
        assert "RHESSI" in frame["hard_source"].iloc[0] or "FERMI" in frame["hard_source"].iloc[0]
    assert len(frame) > 0
    assert "event_id" in events.columns
    assert "flare_class" in events.columns
    assert "scenario" in events.columns


def test_pipeline_contract_goes_mode():
    from arkanetra.config import load_config
    from arkanetra.pipeline import build_dataset

    config = load_config()
    config["data"]["mode"] = "goes_proxy"
    config["data"]["goes_source"] = "sample"
    config["data"]["periods"] = 100

    dataset, events = build_dataset(config)
    required = {"timestamp", "flare_label", "split", "soft_xray_flux", "hard_xray_flux"}
    assert required.issubset(dataset.columns)
    assert set(dataset["split"].drop_duplicates()) == {"train", "validation", "test"}


def test_flare_class_to_severity():
    assert _flare_class_to_severity("X9.3") == 5
    assert _flare_class_to_severity("M2.8") == 4
    assert _flare_class_to_severity("C1.0") == 3
    assert _flare_class_to_severity("B") == 2
    assert _flare_class_to_severity("A") == 1
    assert _flare_class_to_severity("unknown") == 0


def test_scenario_for_class():
    assert _scenario_for_class("X9.3") == "X-class critical replay"
    assert _scenario_for_class("M2.8") == "M-class warning replay"
    assert _scenario_for_class("C1.0") == "C-class watch replay"
    assert _scenario_for_class("background") == "Background archive"
