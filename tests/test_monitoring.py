from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from arkanetra.monitoring.drift import DriftReport, compute_drift_score, detect_drift
from arkanetra.monitoring.retrain import RetrainTrigger
from arkanetra.monitoring.orchestrator import MonitoringOrchestrator, MonitoringCycleResult
from arkanetra.monitoring.continuous_validation import ContinuousValidator, ValidationRecord
from arkanetra.monitoring.status import generate_monitoring_dashboard, monitoring_dashboard_to_markdown


# ---------------------------------------------------------------------------
# Drift Detection
# ---------------------------------------------------------------------------

class TestDriftDetection:
    def _make_data(self, n=200, shift=0.0, seed=42):
        rng = np.random.default_rng(seed)
        cols = ["soft_xray_flux", "hard_xray_flux", "soft_xray_derivative",
                "rolling_mean", "rolling_slope", "rolling_volatility",
                "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope",
                "hard_rolling_mean", "rolling_variance", "waiting_time_since_previous_flare"]
        data = {}
        for c in cols:
            data[c] = rng.normal(0, 1, n) + shift * (1 if c == "soft_xray_flux" else 0)
        return pd.DataFrame(data)

    def test_no_drift_similar_data(self):
        ref = self._make_data(n=200)
        curr = self._make_data(n=200, seed=43)
        report = detect_drift(ref, curr, threshold=0.5)
        assert not report.drift_detected

    def test_drift_detected_with_shift(self):
        ref = self._make_data(n=200)
        curr = self._make_data(n=200, shift=5.0, seed=99)
        report = detect_drift(ref, curr, threshold=0.5)
        assert report.drift_detected
        assert report.drift_score > 0
        assert len(report.drifted_features) > 0

    def test_drift_report_fields(self):
        ref = self._make_data(n=100)
        curr = self._make_data(n=100)
        report = detect_drift(ref, curr)
        assert isinstance(report, DriftReport)
        assert hasattr(report, "drift_detected")
        assert hasattr(report, "drift_score")
        assert hasattr(report, "drifted_features")
        assert hasattr(report, "max_drift_feature")
        assert hasattr(report, "interpretation")
        assert hasattr(report, "threshold")

    def test_compute_drift_score_returns_dict(self):
        ref = self._make_data(n=100)
        curr = self._make_data(n=100)
        scores = compute_drift_score(ref, curr)
        assert isinstance(scores, dict)
        assert len(scores) > 0

    def test_insufficient_data(self):
        ref = self._make_data(n=3)
        curr = self._make_data(n=3)
        report = detect_drift(ref, curr)
        assert not report.drift_detected
        assert "Insufficient" in report.interpretation

    def test_custom_threshold(self):
        ref = self._make_data(n=200)
        curr = self._make_data(n=200, shift=2.0, seed=99)
        report_low = detect_drift(ref, curr, threshold=0.01)
        report_high = detect_drift(ref, curr, threshold=100.0)
        assert report_low.drift_detected
        assert not report_high.drift_detected

    def test_wasserstein_different_lengths(self):
        ref = self._make_data(n=100)
        curr = self._make_data(n=50, seed=99)
        report = detect_drift(ref, curr, threshold=0.5)
        assert isinstance(report, DriftReport)


# ---------------------------------------------------------------------------
# Retrain Trigger
# ---------------------------------------------------------------------------

class TestRetrainTrigger:
    def test_no_retrain_without_archive(self):
        trigger = RetrainTrigger()
        should, reason = trigger.should_retrain()
        assert not should
        assert "No retrain triggers" in reason

    def test_record_drift_check(self):
        trigger = RetrainTrigger()
        report = DriftReport(True, 0.3, ["soft_xray_flux"], "soft_xray_flux", "drift", 0.15)
        trigger.record_drift_check(report)
        assert len(trigger._drift_history) == 1

    def test_consecutive_drifts(self):
        trigger = RetrainTrigger(consecutive_drift_count=2)
        for _ in range(3):
            report = DriftReport(True, 0.3, ["f"], "f", "drift", 0.15)
            trigger.record_drift_check(report)
        assert trigger._count_consecutive_drifts() == 3

    def test_mark_retrained_clears_history(self):
        trigger = RetrainTrigger()
        report = DriftReport(True, 0.3, ["f"], "f", "drift", 0.15)
        trigger.record_drift_check(report)
        trigger.mark_retrained()
        assert len(trigger._drift_history) == 0
        assert trigger._last_retrain_at is not None

    def test_get_status(self):
        trigger = RetrainTrigger()
        status = trigger.get_status()
        assert "last_retrain_at" in status
        assert "consecutive_drifts" in status
        assert "drift_threshold" in status

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "trigger.json"
            trigger1 = RetrainTrigger(state_file=state_file)
            report = DriftReport(True, 0.3, ["f"], "f", "drift", 0.15)
            trigger1.record_drift_check(report)
            trigger1.mark_retrained()

            trigger2 = RetrainTrigger(state_file=state_file)
            assert trigger2._last_retrain_at is not None

    def test_max_age_retrain(self):
        trigger = RetrainTrigger(max_age_hours=0.001)
        trigger._last_retrain_at = "2020-01-01T00:00:00+00:00"
        should, reason = trigger.should_retrain()
        assert should
        assert "age" in reason.lower()


# ---------------------------------------------------------------------------
# Monitoring Orchestrator
# ---------------------------------------------------------------------------

class TestMonitoringOrchestrator:
    def _make_config(self):
        return {
            "monitoring": {
                "drift_threshold": 0.15,
                "consecutive_drift_count": 3,
                "max_age_hours": 168.0,
                "min_runs_before_retrain": 5,
                "retrain_trigger": "manual",
            }
        }

    def _make_predictions(self, n=100, seed=42):
        rng = np.random.default_rng(seed)
        return pd.DataFrame({
            "soft_xray_flux": rng.exponential(1e-6, n),
            "hard_xray_flux": rng.exponential(1e-7, n),
            "soft_xray_derivative": rng.normal(0, 1e-7, n),
            "rolling_mean": rng.exponential(1e-6, n),
            "rolling_slope": rng.normal(0, 1e-7, n),
            "rolling_volatility": rng.exponential(1e-7, n),
            "hardness_ratio": rng.random(n),
            "integrated_hard_xray_energy": rng.exponential(1e-5, n),
            "hard_rolling_slope": rng.normal(0, 1e-7, n),
            "hard_rolling_mean": rng.exponential(1e-7, n),
            "rolling_variance": rng.exponential(1e-14, n),
            "waiting_time_since_previous_flare": rng.exponential(60, n),
            "flare_label": rng.integers(0, 2, n),
            "flare_probability": rng.random(n),
        })

    def test_orchestrator_init(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            assert orch.drift_threshold == 0.15

    def test_run_cycle_basic(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            preds = self._make_predictions()
            ref = self._make_predictions(seed=99)
            result = orch.run_cycle(current_predictions=preds, reference_data=ref)
            assert isinstance(result, MonitoringCycleResult)
            assert result.drift_report is not None
            assert isinstance(result.retrain_reason, str)

    def test_run_cycle_no_predictions(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            result = orch.run_cycle()
            assert result.drift_report is None
            assert not result.retrain_triggered

    def test_run_cycle_with_validate_fn(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))

            def validate():
                return {"passed": True, "f1": 0.85}

            result = orch.run_cycle(validate_fn=validate)
            assert result.validation_passed
            assert result.validation_metrics["f1"] == 0.85

    def test_get_status(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            status = orch.get_status()
            assert "retrain_trigger_mode" in status
            assert "total_cycles" in status
            assert "drift_summary" in status

    def test_generate_report(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            preds = self._make_predictions()
            ref = self._make_predictions(seed=99)
            orch.run_cycle(current_predictions=preds, reference_data=ref)
            report = orch.generate_report()
            assert "Monitoring" in report
            assert "Cycle" in report

    def test_state_persistence(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch1 = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            preds = self._make_predictions()
            ref = self._make_predictions(seed=99)
            orch1.run_cycle(current_predictions=preds, reference_data=ref)

            orch2 = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            assert orch2.get_status()["total_cycles"] == 1


# ---------------------------------------------------------------------------
# Continuous Validation
# ---------------------------------------------------------------------------

class TestContinuousValidator:
    def test_validate_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(baseline_f1=0.8, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
            y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.15, 0.85, 0.1, 0.9])
            record = validator.validate(y_true, y_prob, model_version="v1")
            assert isinstance(record, ValidationRecord)
            assert record.f1_score > 0
            assert record.passed

    def test_validate_fails_on_degradation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(baseline_f1=0.9, f1_threshold=0.05, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
            y_prob = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
            record = validator.validate(y_true, y_prob)
            assert not record.passed

    def test_get_status_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(state_dir=Path(tmpdir))
            status = validator.get_status()
            assert status["total_validations"] == 0

    def test_get_status_with_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(baseline_f1=0.8, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 1, 1])
            y_prob = np.array([0.1, 0.2, 0.8, 0.9])
            validator.validate(y_true, y_prob)
            validator.validate(y_true, y_prob)
            status = validator.get_status()
            assert status["total_validations"] == 2
            assert "mean_f1" in status
            assert "pass_rate" in status

    def test_set_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(state_dir=Path(tmpdir))
            validator.set_baseline(0.85, 0.92)
            assert validator.baseline_f1 == 0.85
            assert validator.baseline_roc_auc == 0.92

    def test_generate_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(baseline_f1=0.8, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 1, 1, 0, 1])
            y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.15, 0.85])
            validator.validate(y_true, y_prob)
            report = validator.generate_report()
            assert "Validation" in report

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = ContinuousValidator(baseline_f1=0.8, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 1, 1])
            y_prob = np.array([0.1, 0.9, 0.8, 0.2])
            v1.validate(y_true, y_prob)

            v2 = ContinuousValidator(state_dir=Path(tmpdir))
            assert v2.get_status()["total_validations"] == 1
            assert v2.baseline_f1 == 0.8

    def test_degradation_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ContinuousValidator(baseline_f1=0.8, f1_threshold=0.1, state_dir=Path(tmpdir))
            y_true = np.array([0, 0, 1, 1])
            y_prob = np.array([0.1, 0.2, 0.8, 0.9])
            record = validator.validate(y_true, y_prob)
            assert record.degradation_from_baseline <= 0.1


# ---------------------------------------------------------------------------
# Monitoring Status Dashboard
# ---------------------------------------------------------------------------

class TestMonitoringStatus:
    def _make_config(self):
        return {
            "monitoring": {
                "drift_threshold": 0.15,
                "consecutive_drift_count": 3,
                "max_age_hours": 168.0,
                "min_runs_before_retrain": 5,
                "retrain_trigger": "manual",
            }
        }

    def test_dashboard_generation(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            validator = ContinuousValidator(baseline_f1=0.8, state_dir=Path(tmpdir))
            dashboard = generate_monitoring_dashboard(orch, validator)
            assert "overall_health" in dashboard
            assert "orchestrator" in dashboard
            assert "validation" in dashboard

    def test_dashboard_healthy(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            dashboard = generate_monitoring_dashboard(orch)
            assert dashboard["overall_health"] == "healthy"
            assert dashboard["health_score"] == 100

    def test_dashboard_markdown(self):
        config = self._make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = MonitoringOrchestrator(config, state_dir=Path(tmpdir))
            dashboard = generate_monitoring_dashboard(orch)
            md = monitoring_dashboard_to_markdown(dashboard)
            assert "Monitoring" in md
            assert "Health" in md


# ---------------------------------------------------------------------------
# Integration with pipeline
# ---------------------------------------------------------------------------

class TestMonitoringIntegration:
    def test_run_mvp_includes_monitoring(self):
        from arkanetra.config import load_config
        from arkanetra.pipeline import run_mvp
        config = load_config()
        config["data"]["periods"] = 120
        config["monitoring"] = {
            "drift_threshold": 0.15,
            "consecutive_drift_count": 3,
            "max_age_hours": 168.0,
            "min_runs_before_retrain": 5,
            "retrain_trigger": "manual",
        }
        result = run_mvp()
        assert "monitoring" in result
        monitoring_path = result["monitoring"]
        assert monitoring_path.exists()
        dashboard_md = monitoring_path / "monitoring_dashboard.md"
        assert dashboard_md.exists()
        val_report = monitoring_path / "validation_report.md"
        assert val_report.exists()

    def test_drift_detects_shift_in_predictions(self):
        from arkanetra.config import load_config
        from arkanetra.pipeline import build_dataset, make_predictions
        config = load_config()
        config["data"]["periods"] = 200
        dataset, events = build_dataset(config)
        predictions, bundle = make_predictions(dataset, config, events)
        y_true = predictions["flare_label"].to_numpy()
        y_prob = predictions["flare_probability"].to_numpy()
        threshold = float(config["model"]["warning_threshold"])

        rng = np.random.default_rng(42)
        ref_data = dataset.head(100).copy()
        ref_data["soft_xray_flux"] = rng.normal(0, 1, 100)
        curr_data = dataset.head(100).copy()
        curr_data["soft_xray_flux"] = rng.normal(5, 1, 100)
        report = detect_drift(ref_data, curr_data, threshold=0.15)
        assert isinstance(report, DriftReport)
