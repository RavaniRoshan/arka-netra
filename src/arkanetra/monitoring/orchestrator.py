from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from arkanetra.monitoring.drift import DriftReport, detect_drift, compute_drift_score
from arkanetra.monitoring.retrain import RetrainTrigger


@dataclass
class MonitoringCycleResult:
    timestamp: str
    drift_report: DriftReport | None
    retrain_triggered: bool
    retrain_reason: str
    validation_passed: bool
    validation_metrics: dict
    cycle_duration_seconds: float


class MonitoringOrchestrator:
    def __init__(
        self,
        config: dict,
        archive=None,
        state_dir: Path | None = None,
    ):
        self.config = config
        self.archive = archive
        monitoring_cfg = config.get("monitoring", {})
        self.drift_threshold = float(monitoring_cfg.get("drift_threshold", 0.15))
        self.consecutive_drift_count = int(monitoring_cfg.get("consecutive_drift_count", 3))
        self.max_age_hours = float(monitoring_cfg.get("max_age_hours", 168.0))
        self.min_runs_before_retrain = int(monitoring_cfg.get("min_runs_before_retrain", 5))
        self.retrain_trigger_mode = monitoring_cfg.get("retrain_trigger", "manual")

        if state_dir is None:
            state_dir = Path("monitoring")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "orchestrator_state.json"

        self.trigger = RetrainTrigger(
            drift_threshold=self.drift_threshold,
            consecutive_drift_count=self.consecutive_drift_count,
            max_age_hours=self.max_age_hours,
            min_runs_before_retrain=self.min_runs_before_retrain,
            state_file=self.state_dir / "retrain_trigger.json",
        )

        self._cycle_history: list[dict] = []
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self._cycle_history = data.get("cycle_history", [])[-20:]
            except Exception:
                pass

    def _save_state(self):
        self.state_file.write_text(
            json.dumps({"cycle_history": self._cycle_history[-20:]}, indent=2, default=str),
            encoding="utf-8",
        )

    def run_cycle(
        self,
        current_predictions: pd.DataFrame | None = None,
        reference_data: pd.DataFrame | None = None,
        train_fn=None,
        validate_fn=None,
    ) -> MonitoringCycleResult:
        start_time = datetime.now(timezone.utc)
        drift_report = None
        retrain_triggered = False
        retrain_reason = ""
        validation_passed = True
        validation_metrics = {}

        if current_predictions is not None and reference_data is not None:
            drift_report = detect_drift(
                reference_data,
                current_predictions,
                threshold=self.drift_threshold,
            )
            self.trigger.record_drift_check(drift_report)

        should_retrain, reason = self.trigger.should_retrain(
            archive=self.archive,
            current_predictions=current_predictions,
            reference_data=reference_data,
        )

        if should_retrain and self.retrain_trigger_mode == "auto" and train_fn is not None:
            retrain_triggered = True
            retrain_reason = reason
            try:
                train_fn()
                self.trigger.mark_retrained()
            except Exception as e:
                retrain_reason = f"Retrain failed: {e}"
                retrain_triggered = False
        elif should_retrain:
            retrain_reason = f"Retrain recommended: {reason} (mode: {self.retrain_trigger_mode})"

        if validate_fn is not None:
            try:
                validation_metrics = validate_fn()
                validation_passed = validation_metrics.get("passed", True)
            except Exception as e:
                validation_metrics = {"passed": False, "error": str(e)}
                validation_passed = False

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        result = MonitoringCycleResult(
            timestamp=start_time.isoformat(),
            drift_report=drift_report,
            retrain_triggered=retrain_triggered,
            retrain_reason=retrain_reason,
            validation_passed=validation_passed,
            validation_metrics=validation_metrics,
            cycle_duration_seconds=duration,
        )

        self._cycle_history.append({
            "timestamp": result.timestamp,
            "drift_detected": drift_report.drift_detected if drift_report else None,
            "drift_score": drift_report.drift_score if drift_report else None,
            "retrain_triggered": retrain_triggered,
            "validation_passed": validation_passed,
            "duration_seconds": duration,
        })
        self._save_state()

        return result

    def get_status(self) -> dict:
        trigger_status = self.trigger.get_status()
        recent_cycles = self._cycle_history[-5:]
        drift_counts = {"detected": 0, "clear": 0}
        for c in self._cycle_history:
            if c.get("drift_detected") is True:
                drift_counts["detected"] += 1
            elif c.get("drift_detected") is False:
                drift_counts["clear"] += 1

        return {
            "retrain_trigger_mode": self.retrain_trigger_mode,
            "drift_threshold": self.drift_threshold,
            "trigger_status": trigger_status,
            "total_cycles": len(self._cycle_history),
            "drift_summary": drift_counts,
            "recent_cycles": recent_cycles,
            "archive_available": self.archive is not None,
        }

    def generate_report(self) -> str:
        status = self.get_status()
        lines = [
            "# ArkaNetra Monitoring Status Report",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Configuration",
            "",
            f"- **Drift Threshold**: {status['drift_threshold']}",
            f"- **Consecutive Drift Count**: {self.consecutive_drift_count}",
            f"- **Max Model Age**: {self.max_age_hours} hours",
            f"- **Retrain Mode**: {status['retrain_trigger_mode']}",
            "",
            "## Trigger Status",
            "",
            f"- **Last Retrain**: {status['trigger_status']['last_retrain_at'] or 'Never'}",
            f"- **Consecutive Drifts**: {status['trigger_status']['consecutive_drifts']}",
            f"- **Drift History Length**: {status['trigger_status']['drift_history_length']}",
            "",
            "## Cycle History",
            "",
            f"- **Total Cycles Run**: {status['total_cycles']}",
            f"- **Drifts Detected**: {status['drift_summary']['detected']}",
            f"- **Clear Checks**: {status['drift_summary']['clear']}",
            "",
        ]
        if status["recent_cycles"]:
            lines.append("### Recent Cycles")
            lines.append("")
            lines.append("| Timestamp | Drift | Retrain | Validation | Duration |")
            lines.append("| --- | --- | --- | --- | --- |")
            for c in status["recent_cycles"]:
                drift_str = "YES" if c.get("drift_detected") else ("no" if c.get("drift_detected") is False else "N/A")
                lines.append(
                    f"| {c['timestamp'][:19]} | {drift_str} | "
                    f"{'YES' if c.get('retrain_triggered') else 'no'} | "
                    f"{'PASS' if c.get('validation_passed') else 'FAIL'} | "
                    f"{c.get('duration_seconds', 0):.1f}s |"
                )
            lines.append("")

        lines.extend([
            "## Limitations",
            "",
            "- Monitoring operates on synthetic proxy data. Real-world drift detection requires operational data.",
            "- Auto-retrain requires `retrain_trigger: auto` in config and a provided training function.",
            "",
        ])
        return "\n".join(lines)
