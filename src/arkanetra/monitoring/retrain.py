from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from arkanetra.monitoring.drift import DriftReport, detect_drift


@dataclass
class RetrainTrigger:
    drift_threshold: float = 0.15
    consecutive_drift_count: int = 3
    max_age_hours: float = 168.0
    min_runs_before_retrain: int = 5
    state_file: Path | None = None

    _drift_history: list[DriftReport] = field(default_factory=list, repr=False)
    _last_retrain_at: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.state_file and self.state_file.exists():
            self._load_state()

    def _load_state(self):
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._drift_history = []
            self._last_retrain_at = data.get("last_retrain_at")
        except Exception:
            pass

    def _save_state(self):
        if self.state_file:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(
                    {
                        "last_retrain_at": self._last_retrain_at,
                        "drift_history_count": len(self._drift_history),
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

    def record_drift_check(self, report: DriftReport):
        self._drift_history.append(report)
        if len(self._drift_history) > 10:
            self._drift_history = self._drift_history[-10:]
        self._save_state()

    def should_retrain(
        self,
        archive=None,
        current_predictions=None,
        reference_data=None,
    ) -> tuple[bool, str]:
        reasons: list[str] = []

        if archive:
            recent_runs = archive.list_runs(limit=max(self.min_runs_before_retrain + 1, 5))
            if len(recent_runs) < self.min_runs_before_retrain:
                return False, f"Only {len(recent_runs)} runs archived; minimum {self.min_runs_before_retrain} required"

            ref_preds = archive.load_predictions(recent_runs[-1]["run_id"])
            latest_preds = archive.load_predictions(recent_runs[0]["run_id"])
            if ref_preds is not None and latest_preds is not None:
                drift_report = detect_drift(
                    ref_preds,
                    latest_preds,
                    threshold=self.drift_threshold,
                )
                self.record_drift_check(drift_report)
                consecutive = self._count_consecutive_drifts()
                if consecutive >= self.consecutive_drift_count:
                    reasons.append(f"{consecutive} consecutive drift detections (threshold: {self.drift_threshold})")

        if current_predictions is not None and reference_data is not None:
            drift_report = detect_drift(reference_data, current_predictions, threshold=self.drift_threshold)
            self.record_drift_check(drift_report)
            if drift_report.drift_detected:
                consecutive = self._count_consecutive_drifts()
                if consecutive >= self.consecutive_drift_count:
                    reasons.append(f"Drift detected in {len(drift_report.drifted_features)} features")

        if self._last_retrain_at:
            last_retrain = datetime.fromisoformat(self._last_retrain_at)
            age_hours = (datetime.now(timezone.utc) - last_retrain).total_seconds() / 3600
            if age_hours > self.max_age_hours:
                reasons.append(f"Model age {age_hours:.1f}h exceeds max {self.max_age_hours}h")

        if reasons:
            return True, "; ".join(reasons)
        return False, "No retrain triggers fired"

    def _count_consecutive_drifts(self) -> int:
        count = 0
        for report in reversed(self._drift_history):
            if report.drift_detected:
                count += 1
            else:
                break
        return count

    def mark_retrained(self):
        self._last_retrain_at = datetime.now(timezone.utc).isoformat()
        self._drift_history.clear()
        self._save_state()

    def get_status(self) -> dict:
        return {
            "last_retrain_at": self._last_retrain_at,
            "consecutive_drifts": self._count_consecutive_drifts(),
            "drift_threshold": self.drift_threshold,
            "drift_history_length": len(self._drift_history),
        }


def should_retrain(
    config: dict,
    archive=None,
    current_predictions=None,
    reference_data=None,
) -> tuple[bool, str]:
    monitoring_cfg = config.get("monitoring", {})
    if not monitoring_cfg.get("retrain_trigger") == "auto":
        return False, "Auto-retrain disabled in config"

    trigger = RetrainTrigger(
        drift_threshold=float(monitoring_cfg.get("drift_threshold", 0.15)),
        consecutive_drift_count=int(monitoring_cfg.get("consecutive_drift_count", 3)),
        max_age_hours=float(monitoring_cfg.get("max_age_hours", 168.0)),
        min_runs_before_retrain=int(monitoring_cfg.get("min_runs_before_retrain", 5)),
    )
    return trigger.should_retrain(archive, current_predictions, reference_data)