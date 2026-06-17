from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from solaris.config import load_config
from solaris.data.hard_xray_proxy import (
    _add_quality_flags,
    _parse_energy_range,
    build_hard_xray_data,
    load_rhessi_from_csv,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _write_minimal_csv(path: Path, times: list[str], flux: list[float]) -> None:
    rows = "\n".join(f"{t},{f}" for t, f in zip(times, flux))
    path.write_text("timestamp,hard_xray_flux\n" + rows, encoding="utf-8")


# ── load_rhessi_from_csv ─────────────────────────────────────────────────────


def test_load_validates_missing_columns(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_rhessi_from_csv(bad)


def test_load_utc_parsed(tmp_path: Path):
    p = tmp_path / "good.csv"
    _write_minimal_csv(p, ["2024-01-01T00:00:00Z", "2024-01-01T00:05:00Z"], [1e-8, 2e-8])
    df = load_rhessi_from_csv(p)
    assert df["timestamp"].dt.tz is not None
    assert len(df) == 2


def test_load_sorted(tmp_path: Path):
    p = tmp_path / "unsorted.csv"
    _write_minimal_csv(p, ["2024-01-01T00:05:00Z", "2024-01-01T00:00:00Z"], [2e-8, 1e-8])
    df = load_rhessi_from_csv(p)
    assert df["timestamp"].iloc[0] < df["timestamp"].iloc[1]


# ── quality flags ─────────────────────────────────────────────────────────────


def test_quality_flags_hard():
    df = pd.DataFrame({"hard_xray_flux": [1e-7, -1.0, np.nan, 1e-13, 0.5]})
    df = _add_quality_flags(df)
    assert df["data_quality"].tolist() == ["ok", "invalid", "invalid", "stale", "suspect_high"]


# ── energy band parsing (no astropy/FITS needed) ───────────────────────────────


def test_parse_energy_range():
    lo, hi = _parse_energy_range("25.0 - 50.0 keV")
    assert lo == 25.0
    assert hi == 50.0


# ── build_hard_xray_data from bundled CSV ─────────────────────────────────────


def test_build_from_sample_csv():
    config = load_config()
    data_cfg = config["data"]
    from solaris.config import ROOT
    sample = ROOT / "data" / "raw" / "goes_sample" / "rhessi_hard_xray_20170905_20170907.csv"
    if not sample.exists():
        pytest.skip("Sample RHESSI CSV not found")

    start = pd.Timestamp("2017-09-05", tz="UTC")
    end = pd.Timestamp("2017-09-07", tz="UTC")
    result = build_hard_xray_data(data_cfg, start, end)

    assert result is not None
    assert "timestamp" in result.columns
    assert "hard_xray_flux" in result.columns
    assert len(result) > 0
    assert result["hard_xray_flux"].min() > 0  # has real flare impulses
    assert result["hard_xray_flux"].max() > 1e-6  # X9.3 peak is ~8.5e-6


def test_build_none_mode_returns_none():
    config = load_config()
    data_cfg = config["data"]
    data_cfg["hard_source"] = "none"
    result = build_hard_xray_data(data_cfg, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-01-02", tz="UTC"))
    assert result is None


def test_build_outside_time_range_returns_none():
    config = load_config()
    data_cfg = config["data"]
    result = build_hard_xray_data(data_cfg, pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2020-01-02", tz="UTC"))
    assert result is None


# ── multimodal pipeline contract ──────────────────────────────────────────────


def test_pipeline_multimodal_contract():
    """GOES + RHESSI together: all features have meaningful non-zero hard X-ray."""
    from solaris.pipeline import build_dataset

    config = load_config()
    config["data"]["mode"] = "goes_proxy"
    config["data"]["goes_source"] = "sample"
    config["data"]["hard_source"] = "auto"
    config["data"]["periods"] = 100

    dataset, events = build_dataset(config)
    assert "hard_xray_flux" in dataset.columns
    assert not dataset["hard_xray_flux"].isna().all()
    assert dataset["hard_xray_flux"].sum() > 0  # not zero-filled
    assert "hardness_ratio" in dataset.columns
    assert not (dataset["hardness_ratio"] == 0).all()  # meaningful ratio


def test_hard_xray_quality_flags_propagate():
    """data_quality column survives pipeline."""
    from solaris.pipeline import build_dataset

    config = load_config()
    config["data"]["mode"] = "goes_proxy"
    config["data"]["goes_source"] = "sample"
    config["data"]["hard_source"] = "auto"
    config["data"]["periods"] = 100

    dataset, _ = build_dataset(config)
    assert "data_quality" in dataset.columns
    assert not dataset["data_quality"].isna().all()
