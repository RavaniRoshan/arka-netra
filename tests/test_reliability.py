from __future__ import annotations

import numpy as np
import pandas as pd

import pytest

from arkanetra.alerts import AlertStateMachine
from arkanetra.data.staleness import (
    compute_staleness_score,
    add_staleness_flags,
    detect_data_gaps,
)


class TestAlertStateMachine:
    def test_normal_state_low_probability(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.1,
            anomaly_index=20.0,
            confidence_low=0.05,
            confidence_high=0.15,
        )
        assert state == "NORMAL"

    def test_watch_state_high_probability(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.4,
            anomaly_index=30.0,
            confidence_low=0.3,
            confidence_high=0.5,
        )
        assert state == "WATCH"

    def test_warning_state(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.6,
            anomaly_index=40.0,
            confidence_low=0.5,
            confidence_high=0.7,
        )
        assert state == "WARNING"

    def test_critical_state(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.85,
            anomaly_index=80.0,
            confidence_low=0.75,
            confidence_high=0.95,
        )
        assert state == "CRITICAL"

    def test_uncertain_state_wide_confidence(self):
        machine = AlertStateMachine(uncertain_confidence_width=0.2)
        state = machine.compute_state(
            flare_probability=0.3,
            anomaly_index=20.0,
            confidence_low=0.0,
            confidence_high=0.5,
        )
        assert state == "UNCERTAIN"

    def test_uncertain_state_stale_data(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.1,
            anomaly_index=20.0,
            confidence_low=0.05,
            confidence_high=0.15,
            is_stale=True,
        )
        assert state == "UNCERTAIN"

    def test_critical_with_anomaly_support(self):
        machine = AlertStateMachine()
        state = machine.compute_state(
            flare_probability=0.70,
            anomaly_index=75.0,
            confidence_low=0.6,
            confidence_high=0.8,
        )
        assert state == "CRITICAL"

    def test_generate_alerts(self):
        machine = AlertStateMachine()
        predictions = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=5, freq="5min", tz="UTC"),
            "flare_probability": [0.1, 0.3, 0.5, 0.7, 0.9],
            "anomaly_index": [20.0, 30.0, 40.0, 60.0, 80.0],
            "confidence_low": [0.05, 0.2, 0.4, 0.6, 0.8],
            "confidence_high": [0.15, 0.4, 0.6, 0.8, 0.95],
            "scenario": ["Quiet"] * 5,
            "data_mode": ["synthetic"] * 5,
            "model_version": ["0.1"] * 5,
        })
        alerts = machine.generate_alerts(predictions, "abc123", "def456")
        assert len(alerts) == 5
        assert alerts[0].state == "NORMAL"
        assert alerts[3].state == "WARNING"
        assert alerts[4].state == "CRITICAL"
        assert alerts[0].config_hash == "abc123"
        assert alerts[0].data_hash == "def456"


class TestStalenessDetection:
    def test_staleness_score_fresh_data(self):
        now = pd.Timestamp.now("UTC")
        dataset = pd.DataFrame({
            "timestamp": [now - pd.Timedelta(hours=1)],
            "soft_xray_flux": [1e-7],
            "data_quality": ["ok"],
        })
        result = compute_staleness_score(dataset)
        assert result["score"] < 50
        assert result["is_stale"] is False

    def test_staleness_score_old_data(self):
        now = pd.Timestamp.now("UTC")
        dataset = pd.DataFrame({
            "timestamp": [now - pd.Timedelta(hours=100)],
            "soft_xray_flux": [1e-7],
            "data_quality": ["suspect_high"],
        })
        result = compute_staleness_score(dataset, max_age_hours=24)
        assert result["is_stale"]
        assert result["score"] > 50
        assert result["score"] > 50

    def test_staleness_score_poor_quality(self):
        now = pd.Timestamp.now("UTC")
        dataset = pd.DataFrame({
            "timestamp": [now - pd.Timedelta(hours=100)] * 10,
            "soft_xray_flux": [1e-7] * 10,
            "data_quality": ["invalid"] * 10,
        })
        result = compute_staleness_score(dataset, max_age_hours=24)
        assert result["is_stale"]
        assert result["score"] > 50

    def test_staleness_score_empty_dataset(self):
        dataset = pd.DataFrame(columns=["timestamp", "soft_xray_flux"])
        result = compute_staleness_score(dataset)
        assert result["score"] == 100
        assert result["is_stale"] is True

    def test_add_staleness_flags(self):
        now = pd.Timestamp.now("UTC")
        dataset = pd.DataFrame({
            "timestamp": [now - pd.Timedelta(hours=100)],
            "soft_xray_flux": [1e-7],
            "data_quality": ["ok"],
        })
        flagged = add_staleness_flags(dataset)
        assert "staleness_score" in flagged.columns
        assert "is_stale" in flagged.columns


class TestDataGapDetection:
    def test_no_gaps(self):
        dataset = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=10, freq="5min", tz="UTC"),
            "soft_xray_flux": [1e-7] * 10,
        })
        result = detect_data_gaps(dataset)
        assert result["has_gaps"] is False
        assert result["gap_count"] == 0

    def test_detects_gaps(self):
        timestamps = list(pd.date_range("2026-01-01", periods=5, freq="5min", tz="UTC"))
        timestamps.insert(2, timestamps[1] + pd.Timedelta(hours=2))
        dataset = pd.DataFrame({
            "timestamp": timestamps,
            "soft_xray_flux": [1e-7] * 6,
        })
        result = detect_data_gaps(dataset, max_gap_count=1)
        assert result["has_gaps"] is True
        assert result["gap_count"] >= 1

    def test_empty_dataset(self):
        dataset = pd.DataFrame(columns=["timestamp", "soft_xray_flux"])
        result = detect_data_gaps(dataset)
        assert result["has_gaps"] is False


class TestConfigHash:
    def test_config_hash_deterministic(self):
        from arkanetra.alerts import config_hash
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 2, "a": 1}
        assert config_hash(config1) == config_hash(config2)

    def test_config_hash_changes_with_content(self):
        from arkanetra.alerts import config_hash
        config1 = {"a": 1}
        config2 = {"a": 2}
        assert config_hash(config1) != config_hash(config2)


class TestDatasetHash:
    def test_dataset_hash_changes_with_content(self):
        from arkanetra.alerts import compute_dataset_hash
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [1, 2, 4]})
        assert compute_dataset_hash(df1) != compute_dataset_hash(df2)