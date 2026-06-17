from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from solaris.data.splits import add_chronological_split, add_event_based_split
from solaris.evaluation import (
    _brier_score,
    _calibration_curve,
    _expected_calibration_error,
    _false_alarm_rate,
    attention_heatmap,
    calibration_plot,
    comprehensive_metric_row,
    false_alarm_analysis,
    lead_time_analysis,
    shap_explanations,
)
from solaris.features import FEATURE_COLUMNS
from solaris.models import metric_row


# ---------------------------------------------------------------------------
# Event-Based Splits
# ---------------------------------------------------------------------------

class TestEventBasedSplit:
    def _make_frame(self, n_events: int = 3, rows_per_event: int = 50) -> pd.DataFrame:
        rows = []
        for i in range(n_events):
            for j in range(rows_per_event):
                rows.append({
                    "timestamp": pd.Timestamp("2017-09-01") + pd.Timedelta(minutes=5 * (i * rows_per_event + j)),
                    "soft_xray_flux": np.random.exponential(1e-6),
                    "hard_xray_flux": np.random.exponential(1e-7),
                    "soft_xray_derivative": np.random.normal(0, 1e-7),
                    "hardness_ratio": np.random.uniform(0, 1),
                    "rolling_mean": np.random.exponential(1e-6),
                    "rolling_slope": np.random.normal(0, 1e-7),
                    "rolling_volatility": np.random.exponential(1e-7),
                    "integrated_hard_xray_energy": np.random.exponential(1e-5),
                    "hard_rolling_slope": np.random.normal(0, 1e-7),
                    "flare_label": int(np.random.random() < 0.1),
                    "upcoming_event_id": f"EVENT-{i}",
                })
        for _ in range(30):
            rows.append({
                "timestamp": pd.Timestamp("2017-09-10") + pd.Timedelta(minutes=5 * _),
                "soft_xray_flux": np.random.exponential(1e-6),
                "hard_xray_flux": np.random.exponential(1e-7),
                "soft_xray_derivative": np.random.normal(0, 1e-7),
                "hardness_ratio": np.random.uniform(0, 1),
                "rolling_mean": np.random.exponential(1e-6),
                "rolling_slope": np.random.normal(0, 1e-7),
                "rolling_volatility": np.random.exponential(1e-7),
                "integrated_hard_xray_energy": np.random.exponential(1e-5),
                "hard_rolling_slope": np.random.normal(0, 1e-7),
                "flare_label": 0,
                "upcoming_event_id": np.nan,
            })
        return pd.DataFrame(rows)

    def test_event_split_has_three_splits(self):
        frame = self._make_frame()
        result = add_event_based_split(frame, train=0.6, validation=0.2)
        assert set(result["split"].unique()) <= {"train", "validation", "test"}

    def test_event_split_no_event_leakage(self):
        frame = self._make_frame(n_events=6, rows_per_event=30)
        result = add_event_based_split(frame, train=0.5, validation=0.25)
        for event_id in result["upcoming_event_id"].dropna().unique():
            splits = result[result["upcoming_event_id"] == event_id]["split"].unique()
            assert len(splits) == 1, f"Event {event_id} leaked across splits: {splits}"

    def test_event_split_has_all_rows(self):
        frame = self._make_frame()
        result = add_event_based_split(frame)
        assert len(result) == len(frame)

    def test_event_split_chronological_fallback(self):
        frame = pd.DataFrame({
            "timestamp": pd.date_range("2017-09-01", periods=100, freq="5min"),
            "upcoming_event_id": np.nan,
            "flare_label": np.zeros(100, dtype=int),
            "soft_xray_flux": np.random.exponential(1e-6, 100),
            "hard_xray_flux": np.random.exponential(1e-7, 100),
        })
        result = add_event_based_split(frame)
        assert set(result["split"].unique()) <= {"train", "validation", "test"}

    def test_event_split_deterministic(self):
        frame = self._make_frame()
        r1 = add_event_based_split(frame)
        r2 = add_event_based_split(frame)
        pd.testing.assert_series_equal(r1["split"], r2["split"])

    def test_event_split_fractions_approximate(self):
        frame = self._make_frame(n_events=10, rows_per_event=20)
        result = add_event_based_split(frame, train=0.6, validation=0.2)
        train_events = set(result[result["split"] == "train"]["upcoming_event_id"].dropna())
        total_events = set(result["upcoming_event_id"].dropna())
        train_frac = len(train_events) / len(total_events)
        assert 0.3 <= train_frac <= 0.9, f"Train fraction {train_frac} out of expected range"


# ---------------------------------------------------------------------------
# Comprehensive Metrics
# ---------------------------------------------------------------------------

class TestComprehensiveMetrics:
    def _perfect_predictions(self):
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.01, 0.02, 0.05, 0.1, 0.9, 0.95, 0.98, 0.99])
        return y_true, y_prob

    def _random_predictions(self, n=200, seed=42):
        rng = np.random.default_rng(seed)
        y_true = rng.integers(0, 2, n)
        y_prob = rng.random(n)
        return y_true, y_prob

    def test_brier_score_perfect(self):
        y_true, y_prob = self._perfect_predictions()
        brier = _brier_score(y_true, y_prob)
        assert brier < 0.05, f"Perfect predictions should have low Brier score, got {brier}"

    def test_brier_score_range(self):
        y_true, y_prob = self._random_predictions()
        brier = _brier_score(y_true, y_prob)
        assert 0 <= brier <= 1

    def test_ece_perfect(self):
        y_true, y_prob = self._perfect_predictions()
        ece = _expected_calibration_error(y_true, y_prob)
        assert ece < 0.1

    def test_ece_range(self):
        y_true, y_prob = self._random_predictions()
        ece = _expected_calibration_error(y_true, y_prob)
        assert 0 <= ece <= 1

    def test_false_alarm_rate(self):
        y_true = np.array([0, 0, 0, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1, 1, 1])
        far = _false_alarm_rate(y_true, y_pred)
        assert abs(far - 0.5) < 1e-6

    def test_calibration_curve(self):
        y_true, y_prob = self._random_predictions()
        mean_probs, mean_true = _calibration_curve(y_true, y_prob)
        assert len(mean_probs) == len(mean_true)
        assert all(0 <= p <= 1 for p in mean_probs)
        assert all(0 <= p <= 1 for p in mean_true)

    def test_comprehensive_metric_row_keys(self):
        y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
        y_prob = np.array([0.1, 0.3, 0.7, 0.9, 0.2, 0.8, 0.15, 0.85])
        row = comprehensive_metric_row("test_model", y_true, y_prob, threshold=0.5)
        expected_keys = {
            "model", "precision", "recall", "f1", "pr_auc", "roc_auc",
            "brier_score", "ece", "false_alarm_rate",
            "true_negative", "false_positive", "false_negative", "true_positive",
            "total_positives", "total_negatives",
        }
        assert expected_keys == set(row.keys())

    def test_comprehensive_metric_row_values(self):
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.01, 0.02, 0.05, 0.1, 0.9, 0.95, 0.98, 0.99])
        row = comprehensive_metric_row("perfect", y_true, y_prob, threshold=0.5)
        assert row["model"] == "perfect"
        assert row["f1"] > 0.9
        assert row["brier_score"] < 0.1

    def test_metric_row_has_brier_and_ece(self):
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_prob = np.array([0.1, 0.4, 0.6, 0.9, 0.2, 0.7])
        row = metric_row("test", y_true, y_prob, threshold=0.5)
        assert "brier_score" in row
        assert "ece" in row
        assert "false_alarm_rate" in row
        assert 0 <= row["brier_score"] <= 1
        assert 0 <= row["ece"] <= 1


# ---------------------------------------------------------------------------
# Lead-Time Analysis
# ---------------------------------------------------------------------------

class TestLeadTimeAnalysis:
    def _make_predictions(self):
        return pd.DataFrame({
            "flare_probability": [0.6, 0.7, 0.8, 0.3, 0.9, 0.5, 0.65, 0.4],
            "time_to_flare_minutes": [20, 45, 60, np.nan, 10, np.nan, 90, np.nan],
        })

    def test_lead_time_returns_dict(self):
        preds = self._make_predictions()
        result = lead_time_analysis(preds, threshold=0.5)
        assert isinstance(result, dict)

    def test_lead_time_keys(self):
        preds = self._make_predictions()
        result = lead_time_analysis(preds, threshold=0.5)
        assert "median_lead_minutes" in result
        assert "mean_lead_minutes" in result
        assert "n_warning_rows" in result

    def test_lead_time_horizon_fractions(self):
        preds = self._make_predictions()
        result = lead_time_analysis(preds, threshold=0.5, horizons=[30, 60])
        assert "fraction_within_30min" in result
        assert "fraction_within_60min" in result
        assert 0 <= result["fraction_within_30min"] <= 1

    def test_lead_time_no_warnings(self):
        preds = pd.DataFrame({
            "flare_probability": [0.1, 0.2, 0.3],
            "time_to_flare_minutes": [10, 20, 30],
        })
        result = lead_time_analysis(preds, threshold=0.9)
        assert result["n_warning_rows"] == 0

    def test_lead_time_custom_horizons(self):
        preds = self._make_predictions()
        result = lead_time_analysis(preds, threshold=0.5, horizons=[15, 45, 120])
        assert "fraction_within_15min" in result
        assert "fraction_within_45min" in result
        assert "fraction_within_120min" in result


# ---------------------------------------------------------------------------
# False Alarm Analysis
# ---------------------------------------------------------------------------

class TestFalseAlarmAnalysis:
    def test_false_alarm_returns_thresholds(self):
        y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
        y_prob = np.array([0.1, 0.3, 0.7, 0.9, 0.2, 0.8, 0.15, 0.85])
        result = false_alarm_analysis(y_true, y_prob, thresholds=[0.3, 0.5, 0.7])
        assert "thresholds" in result
        assert len(result["thresholds"]) == 3
        for row in result["thresholds"]:
            assert "threshold" in row
            assert "false_alarm_rate" in row
            assert "recall" in row

    def test_higher_threshold_fewer_alarms(self):
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
        result = false_alarm_analysis(y_true, y_prob, thresholds=[0.3, 0.7])
        far_low = result["thresholds"][0]["false_alarm_rate"]
        far_high = result["thresholds"][1]["false_alarm_rate"]
        assert far_high <= far_low

    def test_default_thresholds(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.2, 0.4, 0.6, 0.8])
        result = false_alarm_analysis(y_true, y_prob)
        assert len(result["thresholds"]) == 7


# ---------------------------------------------------------------------------
# Attention Heatmap
# ---------------------------------------------------------------------------

class TestAttentionHeatmap:
    def test_heatmap_creates_file(self, tmp_path):
        from solaris.evaluation import HAS_MATPLOTLIB
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not installed")
        attention = pd.DataFrame(np.random.random((8, 8)))
        output = tmp_path / "heatmap.png"
        result = attention_heatmap(attention, output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_heatmap_custom_title(self, tmp_path):
        from solaris.evaluation import HAS_MATPLOTLIB
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not installed")
        attention = pd.DataFrame(np.random.random((6, 6)))
        output = tmp_path / "custom.png"
        result = attention_heatmap(attention, output, title="Custom Title")
        assert result.exists()

    def test_heatmap_creates_parent_dir(self, tmp_path):
        from solaris.evaluation import HAS_MATPLOTLIB
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not installed")
        attention = pd.DataFrame(np.random.random((4, 4)))
        output = tmp_path / "subdir" / "heatmap.png"
        result = attention_heatmap(attention, output)
        assert result.exists()


# ---------------------------------------------------------------------------
# Calibration Plot
# ---------------------------------------------------------------------------

class TestCalibrationPlot:
    def test_calibration_creates_file(self, tmp_path):
        from solaris.evaluation import HAS_MATPLOTLIB
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not installed")
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
        output = tmp_path / "calibration.png"
        result = calibration_plot(y_true, y_prob, output, model_name="Test Model")
        assert result.exists()
        assert result.stat().st_size > 0


# ---------------------------------------------------------------------------
# SHAP Explanations
# ---------------------------------------------------------------------------

class TestShapExplanations:
    def test_shap_returns_dict(self):
        from solaris.models import SolarisFusionModel
        rng = np.random.default_rng(42)
        n = 100
        frame = pd.DataFrame({c: rng.random(n) for c in FEATURE_COLUMNS})
        frame["flare_label"] = rng.integers(0, 2, n)
        model = SolarisFusionModel(random_seed=42, neupert_lambda=0.18)
        model.fit(frame)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = shap_explanations(model, frame, FEATURE_COLUMNS, Path(tmpdir))
        assert isinstance(result, dict)

    def test_shap_top_features(self):
        from solaris.models import SolarisFusionModel
        rng = np.random.default_rng(42)
        n = 100
        frame = pd.DataFrame({c: rng.random(n) for c in FEATURE_COLUMNS})
        frame["flare_label"] = rng.integers(0, 2, n)
        model = SolarisFusionModel(random_seed=42, neupert_lambda=0.18)
        model.fit(frame)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = shap_explanations(model, frame, FEATURE_COLUMNS, Path(tmpdir))
        if result.get("available"):
            assert "top_features" in result
            assert len(result["top_features"]) > 0


# ---------------------------------------------------------------------------
# Integration: Evaluation with build_dataset
# ---------------------------------------------------------------------------

class TestEvaluationIntegration:
    def test_comprehensive_metrics_on_pipeline_data(self):
        from solaris.config import load_config
        from solaris.pipeline import build_dataset, make_predictions
        config = load_config()
        dataset, events = build_dataset(config)
        predictions, bundle = make_predictions(dataset, config, events)
        y_true = predictions["flare_label"].to_numpy()
        y_prob = predictions["flare_probability"].to_numpy()
        threshold = float(config["model"]["warning_threshold"])
        row = comprehensive_metric_row("pipeline_model", y_true, y_prob, threshold)
        assert row["model"] == "pipeline_model"
        assert 0 <= row["f1"] <= 1
        assert 0 <= row["brier_score"] <= 1

    def test_lead_time_on_pipeline_predictions(self):
        from solaris.config import load_config
        from solaris.pipeline import build_dataset, make_predictions
        config = load_config()
        dataset, events = build_dataset(config)
        predictions, _ = make_predictions(dataset, config, events)
        threshold = float(config["model"]["warning_threshold"])
        result = lead_time_analysis(predictions, threshold)
        assert isinstance(result, dict)
        assert "median_lead_minutes" in result

    def test_event_split_on_pipeline_data(self):
        from solaris.config import load_config
        from solaris.pipeline import build_dataset
        config = load_config()
        config["evaluation"] = {"event_based_splits": True}
        dataset, events = build_dataset(config)
        assert "split" in dataset.columns
        assert len(dataset["split"].unique()) >= 2
