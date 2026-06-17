from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

import pytest

from solaris.config import ROOT
from solaris.data.hel1os import (
    load_hel1os_csv,
    _add_quality_flags,
    _resample_to_cadence,
    build_hel1os_replay,
)


SAMPLE_DIR = ROOT / "data" / "raw" / "aditya_l1_sample"


class TestLoadHel1osCsv:
    def test_load_hel1os_csv_required_columns(self, tmp_path):
        csv_file = tmp_path / "hel1os_test.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z"],
            "hard_xray_flux": [1e-9, 2e-9],
        })
        df.to_csv(csv_file, index=False)
        loaded = load_hel1os_csv(csv_file)
        assert "timestamp" in loaded.columns
        assert "hard_xray_flux" in loaded.columns
        assert len(loaded) == 2

    def test_load_hel1os_csv_missing_column_raises(self, tmp_path):
        csv_file = tmp_path / "hel1os_bad.csv"
        df = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"]})
        df.to_csv(csv_file, index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_hel1os_csv(csv_file)

    def test_load_hel1os_csv_sorts_by_timestamp(self, tmp_path):
        csv_file = tmp_path / "hel1os_unsorted.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-01-01T01:00:00Z", "2026-01-01T00:00:00Z"],
            "hard_xray_flux": [1e-9, 2e-9],
        })
        df.to_csv(csv_file, index=False)
        loaded = load_hel1os_csv(csv_file)
        assert loaded["timestamp"].iloc[0] <= loaded["timestamp"].iloc[1]


class TestHel1osQualityFlags:
    def test_quality_ok(self):
        frame = pd.DataFrame({"hard_xray_flux": [1e-8]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "ok"

    def test_quality_stale_low_flux(self):
        frame = pd.DataFrame({"hard_xray_flux": [1e-14]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "stale"

    def test_quality_suspect_high(self):
        frame = pd.DataFrame({"hard_xray_flux": [1e0]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "suspect_high"

    def test_quality_invalid_negative(self):
        frame = pd.DataFrame({"hard_xray_flux": [-1e-9]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "invalid"

    def test_quality_invalid_nan(self):
        frame = pd.DataFrame({"hard_xray_flux": [float("nan")]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "invalid"


class TestHel1osResample:
    def test_resample_changes_cadence(self):
        base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        frame = pd.DataFrame({
            "timestamp": [base + pd.Timedelta(minutes=i) for i in range(10)],
            "hard_xray_flux": [1e-9] * 10,
        })
        resampled = _resample_to_cadence(frame, cadence_minutes=5)
        assert len(resampled) <= len(frame)

    def test_resample_adds_quality_flags(self):
        base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        frame = pd.DataFrame({
            "timestamp": [base + pd.Timedelta(minutes=i) for i in range(10)],
            "hard_xray_flux": [1e-9] * 10,
        })
        resampled = _resample_to_cadence(frame, cadence_minutes=5)
        assert "data_quality" in resampled.columns


class TestBuildHel1osReplay:
    def test_build_hel1os_replay_with_sample(self):
        data_cfg = {
            "cadence_minutes": 5,
            "aditya_l1": {
                "hard_source": "hel1os_sample",
                "hel1os_energy_band": "25-100 keV",
            }
        }
        time_start = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        time_end = pd.Timestamp("2026-01-02T00:00:00", tz="UTC")
        result = build_hel1os_replay(data_cfg, time_start, time_end)
        if result is not None:
            assert "timestamp" in result.columns
            assert "hard_xray_flux" in result.columns
            assert "hard_instrument" in result.columns

    def test_build_hel1os_replay_none_source_returns_none(self):
        data_cfg = {
            "cadence_minutes": 5,
            "aditya_l1": {
                "hard_source": "none",
            }
        }
        time_start = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        time_end = pd.Timestamp("2026-01-02T00:00:00", tz="UTC")
        result = build_hel1os_replay(data_cfg, time_start, time_end)
        assert result is None

    def test_build_hel1os_replay_outside_window_returns_empty(self):
        data_cfg = {
            "cadence_minutes": 5,
            "aditya_l1": {
                "hard_source": "hel1os_sample",
                "hel1os_energy_band": "25-100 keV",
            }
        }
        time_start = pd.Timestamp("2025-01-01T00:00:00", tz="UTC")
        time_end = pd.Timestamp("2025-01-02T00:00:00", tz="UTC")
        result = build_hel1os_replay(data_cfg, time_start, time_end)
        if result is not None:
            assert result.empty


class TestHel1osSchema:
    def test_sample_data_loads(self):
        sample_path = SAMPLE_DIR / "hel1os_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_hel1os_csv(sample_path)
            assert len(df) > 0
            assert "timestamp" in df.columns
            assert "hard_xray_flux" in df.columns
            assert "data_quality" in df.columns
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_data_has_valid_timestamps(self):
        sample_path = SAMPLE_DIR / "hel1os_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_hel1os_csv(sample_path)
            assert df["timestamp"].dt.tz is not None
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_data_quality_flags_present(self):
        sample_path = SAMPLE_DIR / "hel1os_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_hel1os_csv(sample_path)
            valid_flags = {"ok", "stale", "suspect_high", "invalid"}
            assert set(df["data_quality"].unique()).issubset(valid_flags)
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_data_energy_band_present(self):
        sample_path = SAMPLE_DIR / "hel1os_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_hel1os_csv(sample_path)
            assert "energy_band" in df.columns
        else:
            pytest.skip("Sample data not generated yet")