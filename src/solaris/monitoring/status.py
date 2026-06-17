from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from solaris.monitoring.orchestrator import MonitoringOrchestrator
from solaris.monitoring.continuous_validation import ContinuousValidator
from solaris.monitoring.drift import DriftReport
from solaris.monitoring.retrain import RetrainTrigger


def generate_monitoring_dashboard(
    orchestrator: MonitoringOrchestrator,
    validator: ContinuousValidator | None = None,
) -> dict:
    orch_status = orchestrator.get_status()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "orchestrator": orch_status,
        "validation": None,
        "overall_health": "unknown",
    }

    if validator is not None:
        val_status = validator.get_status()
        result["validation"] = val_status

    health_score = 100
    issues = []

    if orch_status["trigger_status"]["consecutive_drifts"] > 0:
        drifts = orch_status["trigger_status"]["consecutive_drifts"]
        health_score -= drifts * 10
        issues.append(f"{drifts} consecutive drift detections")

    if orch_status["retrain_trigger_mode"] == "manual":
        issues.append("Auto-retrain disabled (manual mode)")

    if result["validation"] is not None:
        val = result["validation"]
        if val["total_validations"] > 0:
            if val["pass_rate"] < 0.8:
                health_score -= 20
                issues.append(f"Validation pass rate {val['pass_rate']:.0%} < 80%")
            if val.get("std_f1", 0) > 0.1:
                health_score -= 10
                issues.append(f"F1 std dev {val.get('std_f1', 0):.4f} > 0.1")

    health_score = max(0, health_score)
    if health_score >= 80:
        result["overall_health"] = "healthy"
    elif health_score >= 50:
        result["overall_health"] = "degraded"
    else:
        result["overall_health"] = "unhealthy"

    result["health_score"] = health_score
    result["issues"] = issues

    return result


def monitoring_dashboard_to_markdown(dashboard: dict) -> str:
    health = dashboard.get("overall_health", "unknown")
    score = dashboard.get("health_score", 0)
    health_emoji = {"healthy": "OK", "degraded": "WARN", "unhealthy": "CRIT"}.get(health, "???")

    lines = [
        "# Solaris Monitoring Dashboard",
        "",
        f"Generated: {dashboard.get('generated_at', 'N/A')}",
        "",
        f"## Overall Health: [{health_emoji}] {health.upper()} (score: {score}/100)",
        "",
    ]

    issues = dashboard.get("issues", [])
    if issues:
        lines.append("### Issues")
        lines.append("")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")

    orch = dashboard.get("orchestrator", {})
    lines.extend([
        "## Drift Monitoring",
        "",
        f"- **Drift Threshold**: {orch.get('drift_threshold', 'N/A')}",
        f"- **Retrain Mode**: {orch.get('retrain_trigger_mode', 'N/A')}",
        f"- **Total Cycles**: {orch.get('total_cycles', 0)}",
        f"- **Consecutive Drifts**: {orch.get('trigger_status', {}).get('consecutive_drifts', 0)}",
        f"- **Last Retrain**: {orch.get('trigger_status', {}).get('last_retrain_at', 'Never')}",
        "",
    ])

    val = dashboard.get("validation")
    if val is not None:
        lines.extend([
            "## Validation Status",
            "",
            f"- **Total Validations**: {val.get('total_validations', 0)}",
        ])
        if val.get("total_validations", 0) > 0:
            lines.extend([
                f"- **Mean F1**: {val.get('mean_f1', 0):.4f}",
                f"- **Pass Rate**: {val.get('pass_rate', 0):.1%}",
                f"- **F1 Range**: {val.get('min_f1', 0):.4f} - {val.get('max_f1', 0):.4f}",
            ])
        lines.append("")

    recent = orch.get("recent_cycles", [])
    if recent:
        lines.append("## Recent Monitoring Cycles")
        lines.append("")
        lines.append("| Time | Drift | Retrain | Validation | Duration |")
        lines.append("| --- | --- | --- | --- | --- |")
        for c in recent:
            drift = "YES" if c.get("drift_detected") else ("no" if c.get("drift_detected") is False else "N/A")
            lines.append(
                f"| {c['timestamp'][:19]} | {drift} | "
                f"{'YES' if c.get('retrain_triggered') else 'no'} | "
                f"{'PASS' if c.get('validation_passed') else 'FAIL'} | "
                f"{c.get('duration_seconds', 0):.1f}s |"
            )
        lines.append("")

    lines.extend([
        "## Limitations",
        "",
        "- Monitoring operates on synthetic proxy data.",
        "- Auto-retrain requires `retrain_trigger: auto` in config.",
        "- Continuous validation requires a baseline model to compare against.",
        "",
    ])

    return "\n".join(lines)
