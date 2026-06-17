from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score


@dataclass
class ValidationRecord:
    timestamp: str
    model_version: str
    f1_score: float
    roc_auc: float
    n_samples: int
    n_positive: int
    passed: bool
    degradation_from_baseline: float
    notes: str


class ContinuousValidator:
    def __init__(
        self,
        baseline_f1: float = 0.0,
        baseline_roc_auc: float = 0.0,
        f1_threshold: float = 0.1,
        state_dir: Path | None = None,
    ):
        self.baseline_f1 = baseline_f1
        self.baseline_roc_auc = baseline_roc_auc
        self.f1_threshold = f1_threshold
        if state_dir is None:
            state_dir = Path("monitoring")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "validation_history.json"
        self._history: list[dict] = []
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self._history = data.get("records", [])[-50:]
                self.baseline_f1 = data.get("baseline_f1", self.baseline_f1)
                self.baseline_roc_auc = data.get("baseline_roc_auc", self.baseline_roc_auc)
            except Exception:
                pass

    def _save_state(self):
        self.state_file.write_text(
            json.dumps(
                {
                    "baseline_f1": self.baseline_f1,
                    "baseline_roc_auc": self.baseline_roc_auc,
                    "records": self._history[-50:],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def validate(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        model_version: str = "unknown",
        threshold: float = 0.55,
    ) -> ValidationRecord:
        y_pred = (y_prob >= threshold).astype(int)
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        if len(np.unique(y_true)) >= 2:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        else:
            roc_auc = 0.0

        degradation = self.baseline_f1 - f1
        passed = degradation <= self.f1_threshold

        record = ValidationRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_version=model_version,
            f1_score=f1,
            roc_auc=roc_auc,
            n_samples=len(y_true),
            n_positive=int(y_true.sum()),
            passed=passed,
            degradation_from_baseline=degradation,
            notes=f"F1={f1:.4f}, baseline={self.baseline_f1:.4f}, delta={degradation:.4f}",
        )

        self._history.append({
            "timestamp": record.timestamp,
            "model_version": record.model_version,
            "f1_score": record.f1_score,
            "roc_auc": record.roc_auc,
            "n_samples": record.n_samples,
            "passed": record.passed,
            "degradation": record.degradation_from_baseline,
        })
        self._save_state()

        return record

    def get_status(self) -> dict:
        if not self._history:
            return {
                "total_validations": 0,
                "baseline_f1": self.baseline_f1,
                "baseline_roc_auc": self.baseline_roc_auc,
                "f1_threshold": self.f1_threshold,
                "recent_results": [],
            }

        recent = self._history[-5:]
        all_f1 = [r["f1_score"] for r in self._history]
        pass_rate = sum(1 for r in self._history if r["passed"]) / len(self._history)

        return {
            "total_validations": len(self._history),
            "baseline_f1": self.baseline_f1,
            "baseline_roc_auc": self.baseline_roc_auc,
            "f1_threshold": self.f1_threshold,
            "mean_f1": float(np.mean(all_f1)),
            "std_f1": float(np.std(all_f1)),
            "min_f1": float(np.min(all_f1)),
            "max_f1": float(np.max(all_f1)),
            "pass_rate": pass_rate,
            "recent_results": recent,
        }

    def set_baseline(self, f1: float, roc_auc: float):
        self.baseline_f1 = f1
        self.baseline_roc_auc = roc_auc
        self._save_state()

    def generate_report(self) -> str:
        status = self.get_status()
        lines = [
            "# ArkaNetra Continuous Validation Report",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Baseline",
            "",
            f"- **F1 Baseline**: {status['baseline_f1']:.4f}",
            f"- **ROC-AUC Baseline**: {status['baseline_roc_auc']:.4f}",
            f"- **Degradation Threshold**: {status['f1_threshold']}",
            "",
            "## Summary",
            "",
            f"- **Total Validations**: {status['total_validations']}",
        ]
        if status["total_validations"] > 0:
            lines.extend([
                f"- **Mean F1**: {status['mean_f1']:.4f}",
                f"- **Std F1**: {status['std_f1']:.4f}",
                f"- **Min F1**: {status['min_f1']:.4f}",
                f"- **Max F1**: {status['max_f1']:.4f}",
                f"- **Pass Rate**: {status['pass_rate']:.1%}",
            ])
        lines.append("")

        if status["recent_results"]:
            lines.append("### Recent Validations")
            lines.append("")
            lines.append("| Timestamp | Model | F1 | ROC-AUC | Samples | Passed |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for r in status["recent_results"]:
                lines.append(
                    f"| {r['timestamp'][:19]} | {r['model_version'][:20]} | "
                    f"{r['f1_score']:.4f} | {r['roc_auc']:.4f} | "
                    f"{r['n_samples']} | {'PASS' if r['passed'] else 'FAIL'} |"
                )
            lines.append("")

        return "\n".join(lines)
