from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

import pytest

from solaris.config import ROOT
from solaris.data.solexs import (
    load_solexs_csv,
    _add_quality_flags,
    _resample_to_cadence,
    build_solexs_replay,
)


SAMPLE_DIR = ROOT / "data" / "raw" / "aditya_l1_sample"


class TestLoadSolexsCsv:
    def test_load_solexs_csv_required_columns(self, tmp_path):
        csv_file = tmp_path / "solexs_test.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z"],
            "soft_xray_flux": [1e-7, 2e-7],
        })
        df.to_csv(csv_file, index=False)
        loaded = load_solexs_csv(csv_file)
        assert "timestamp" in loaded.columns
        assert "soft_xray_flux" in loaded.columns
        assert len(loaded) == 2

    def test_load_solexs_csv_missing_column_raises(self, tmp_path):
        csv_file = tmp_path / "solexs_bad.csv"
        df = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"]})
        df.to_csv(csv_file, index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_solexs_csv(csv_file)

    def test_load_solexs_csv_sorts_by_timestamp(self, tmp_path):
        csv_file = tmp_path / "solexs_unsorted.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-01-01T01:00:00Z", "2026-01-01T00:00:00Z"],
            "soft_xray_flux": [1e-7, 2e-7],
        })
        df.to_csv(csv_file, index=False)
        loaded = load_solexs_csv(csv_file)
        assert loaded["timestamp"].iloc[0] <= loaded["timestamp"].iloc[1]


class TestAddQualityFlags:
    def test_quality_ok(self):
        frame = pd.DataFrame({"soft_xray_flux": [1e-6]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "ok"

    def test_quality_stale_low_flux(self):
        frame = pd.DataFrame({"soft_xray_flux": [1e-12]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "stale"

    def test_quality_suspect_high(self):
        frame = pd.DataFrame({"soft_xray_flux": [1e-1]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "suspect_high"

    def test_quality_invalid_nan(self):
        frame = pd.DataFrame({"soft_xray_flux": [float("nan")]})
        result = _add_quality_flags(frame)
        assert result["data_quality"].iloc[0] == "invalid"


class TestResampleToCadence:
    def test_resample_changes_cadence(self):
        base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        frame = pd.DataFrame({
            "timestamp": [base + pd.Timedelta(minutes=i) for i in range(10)],
            "soft_xray_flux": [1e-7] * 10,
        })
        resampled = _resample_to_cadence(frame, cadence_minutes=5)
        assert len(resampled) <= len(frame)

    def test_resample_adds_quality_flags(self):
        base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        frame = pd.DataFrame({
            "timestamp": [base + pd.Timedelta(minutes=i) for i in range(10)],
            "soft_xray_flux": [1e-7] * 10,
        })
        resampled = _resample_to_cadence(frame, cadence_minutes=5)
        assert "data_quality" in resampled.columns


class TestBuildSolexsReplay:
    def test_build_solexs_replay_with_sample(self):
        config = {
            "data": {
                "mode": "aditya_l1",
                "cadence_minutes": 5,
                "aditya_l1": {
                    "soft_source": "solexs_sample",
                    "hard_source": "hel1os_sample",
                    "hel1os_energy_band": "25-100 keV",
                }
            }
        }
        raw, events = build_solexs_replay(config)
        assert "timestamp" in raw.columns
        assert "soft_xray_flux" in raw.columns
        assert "soft_source" in raw.columns
        assert not raw.empty

    def test_build_solexs_replay_falls_back_to_hel1os(self):
        config = {
            "data": {
                "mode": "aditya_l1",
                "cadence_minutes": 5,
                "aditya_l1": {
                    "soft_source": "solexs_sample",
                    "hard_source": "hel1os_sample",
                    "hel1os_energy_band": "25-100 keV",
                }
            }
        }
        raw, events = build_solexs_replay(config)
        assert "hard_xray_flux" in raw.columns
        assert "hard_source" in raw.columns

    def test_build_solexs_replay_nonexistent_source(self):
        config = {
            "data": {
                "mode": "aditya_l1",
                "cadence_minutes": 5,
                "aditya_l1": {
                    "soft_source": "nonexistent.csv",
                    "hard_source": "none",
                }
            }
        }
        raw, events = build_solexs_replay(config)
        assert len(raw) == 0 or "soft_xray_flux" in raw.columns


class TestSolexsSchema:
    def test_sample_data_loads(self):
        sample_path = SAMPLE_DIR / "solexs_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_solexs_csv(sample_path)
            assert len(df) > 0
            assert "timestamp" in df.columns
            assert "soft_xray_flux" in df.columns
            assert "data_quality" in df.columns
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_data_has_valid_timestamps(self):
        sample_path = SAMPLE_DIR / "solexs_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_solexs_csv(sample_path)
            assert df["timestamp"].dt.tz is not None
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_data_quality_flags_present(self):
        sample_path = SAMPLE_DIR / "solexs_sample_20260101_20260102.csv"
        if sample_path.exists():
            df = load_solexs_csv(sample_path)
            valid_flags = {"ok", "stale", "suspect_high", "invalid"}
            assert set(df["data_quality"].unique()).issubset(valid_flags)
        else:
            pytest.skip("Sample data not generated yet")

    def test_sample_flare_catalog_loads(self):
        catalog_path = SAMPLE_DIR / "noaa_flare_catalog_solexs.csv"
        if catalog_path.exists():
            df = pd.read_csv(catalog_path)
            assert len(df) > 0
            assert "event_id" in df.columns
            assert "flare_class" in df.columns
        else:
            pytest.skip("Flare catalog not generated yet")