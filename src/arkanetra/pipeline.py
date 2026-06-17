from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from arkanetra.alerts import (
    AlertStateMachine,
    config_hash as compute_config_hash,
    data_hash as compute_data_hash,
    compute_dataset_hash,
    write_audit_log,
)
from arkanetra.anomaly import compute_anomaly_index
from arkanetra.config import ROOT, ensure_directories, load_config
from arkanetra.data.splits import add_chronological_split, add_event_based_split
from arkanetra.data.synthetic import build_synthetic_proxy_data
from arkanetra.data.staleness import compute_staleness_score, add_staleness_flags
from arkanetra.data.windows import add_forecast_labels
from arkanetra.features import FEATURE_COLUMNS, add_features
from arkanetra.models import monte_carlo_uncertainty, train_models


def build_dataset(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_mode = config.get("data", {}).get("mode", "synthetic")
    if data_mode == "goes_proxy":
        from arkanetra.data.goes import build_goes_replay
        raw, events = build_goes_replay(config)
    elif data_mode == "aditya_l1":
        from arkanetra.data.solexs import build_solexs_replay
        raw, events = build_solexs_replay(config)
    else:
        raw, events = build_synthetic_proxy_data(config)
    featured = add_features(raw, events, config)
    labeled = add_forecast_labels(featured, events, int(config["data"]["forecast_horizon_minutes"]))
    eval_cfg = config.get("evaluation", {})
    if eval_cfg.get("event_based_splits", False):
        split = add_event_based_split(labeled)
    else:
        split = add_chronological_split(labeled)
    return split, events


def scenario_for_row(row: pd.Series) -> str:
    if row.get("upcoming_event_id"):
        klass = str(row.get("upcoming_flare_class", "flare"))[:1].upper()
        if klass == "X":
            return "X-class critical replay"
        if klass == "M":
            return "M-class warning replay"
        return "C-class watch replay"
    return "Quiet Sun replay"


def make_predictions(dataset: pd.DataFrame, config: dict, events: pd.DataFrame | None = None):
    bundle = train_models(dataset, config)
    probability = bundle.final_model.predict_proba(dataset)
    mean, variance, low, high = monte_carlo_uncertainty(
        probability,
        int(config["model"]["mc_dropout_passes"]),
        int(config["model"]["random_seed"]),
    )
    predictions = dataset[
        [
            "timestamp",
            "soft_xray_flux",
            "hard_xray_flux",
            "hardness_ratio",
            "soft_xray_derivative",
            "integrated_hard_xray_energy",
            "flare_label",
            "upcoming_event_id",
            "upcoming_flare_class",
            "time_to_flare_minutes",
            "split",
        ]
    ].copy()
    predictions["flare_probability"] = mean
    predictions["uncertainty_variance"] = variance
    predictions["confidence_low"] = low
    predictions["confidence_high"] = high
    predictions["anomaly_index"] = compute_anomaly_index(dataset, config)
    predictions["scenario"] = "Background archive"
    predictions["mission_state"] = predictions.apply(lambda row: _mission_state(row, config), axis=1)
    data_mode = config.get("data", {}).get("mode", "synthetic")
    if data_mode == "aditya_l1":
        predictions["data_mode"] = "aditya_l1_mission_replay"
    elif data_mode == "goes_proxy":
        predictions["data_mode"] = "goes_proxy_replay"
    else:
        predictions["data_mode"] = "synthetic_proxy_replay"
    predictions["model_version"] = config["project"]["version"]
    predictions["scenario"] = assign_demo_scenarios(predictions, events)
    predictions = _add_radiation_context(predictions, config)
    return predictions, bundle


def assign_demo_scenarios(predictions: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.Series:
    """Assign curated replay scenarios driven by event IDs from the data source."""
    scenarios = pd.Series("Background archive", index=predictions.index, dtype="object")
    cadence_minutes = predictions["timestamp"].diff().dt.total_seconds().div(60).median()
    if not np.isfinite(cadence_minutes) or cadence_minutes <= 0:
        cadence_minutes = 5
    quiet_steps = int(round(8 * 60 / cadence_minutes))
    quiet_candidates = _best_quiet_window(predictions, quiet_steps)
    scenarios.loc[quiet_candidates] = "Quiet Sun replay"

    if events is not None and not events.empty:
        event_map = dict(zip(events["event_id"], events["scenario"]))
    else:
        event_map = {
            "SOL-C-001": "C-class watch replay",
            "SOL-M-002": "M-class warning replay",
            "SOL-X-003": "X-class critical replay",
        }

    for event_id in predictions["upcoming_event_id"].unique():
        event_str = str(event_id) if pd.notna(event_id) else ""
        if not event_str:
            continue
        scenario = event_map.get(event_str, "Background archive")
        scenarios.loc[predictions["upcoming_event_id"].eq(event_str)] = scenario

    return scenarios


def _best_quiet_window(predictions: pd.DataFrame, quiet_steps: int) -> pd.Index:
    clean = predictions[predictions["flare_label"].eq(0)].copy()
    if len(clean) <= quiet_steps:
        return clean.index
    score = clean["flare_probability"].astype(float) + clean["anomaly_index"].astype(float).div(100)
    rolling = score.rolling(quiet_steps, min_periods=quiet_steps).mean()
    if rolling.dropna().empty:
        return clean.head(quiet_steps).index
    end_label = rolling.idxmin()
    end_position = clean.index.get_loc(end_label)
    start_position = max(0, end_position - quiet_steps + 1)
    return clean.iloc[start_position : end_position + 1].index


def _mission_state(row: pd.Series, config: dict) -> str:
    policy = config.get("alert_policy", {})
    watch_probability = float(policy.get("watch_probability", 0.35))
    warning_probability = float(policy.get("warning_probability", 0.55))
    critical_probability = float(policy.get("critical_probability", 0.78))
    anomaly_watch = float(policy.get("anomaly_watch", 45))
    anomaly_supporting_warning = float(policy.get("anomaly_supporting_warning", 70))
    p = float(row["flare_probability"])
    a = float(row["anomaly_index"])
    if p >= critical_probability or (p >= warning_probability + 0.10 and a >= anomaly_supporting_warning):
        return "CRITICAL"
    if p >= warning_probability:
        return "WARNING"
    if p >= watch_probability or a >= anomaly_watch:
        return "WATCH"
    return "NORMAL"


def _add_radiation_context(predictions: pd.DataFrame, config: dict) -> pd.DataFrame:
    radiation_cfg = config.get("radiation", {})
    sep_enabled = radiation_cfg.get("sep_enabled", False)

    if not sep_enabled:
        predictions["sep_risk_context"] = predictions.apply(_sep_context_fallback, axis=1)
        return predictions

    try:
        from arkanetra.radiation import compute_sep_risk_index, fetch_goes_particle_data

        particle_source = radiation_cfg.get("particle_source", "none")
        enable_particle = particle_source != "none"

        particle_data = None
        if enable_particle:
            now = datetime.now(timezone.utc)
            particle_data = fetch_goes_particle_data(start=now - timedelta(hours=6), end=now)

        predictions = compute_sep_risk_index(
            predictions,
            particle_data=particle_data,
            enable_particle_integration=enable_particle,
        )
        satellite_risk_enabled = radiation_cfg.get("satellite_risk_enabled", False)
        if satellite_risk_enabled:
            from arkanetra.radiation import SatelliteOrbit, assess_satellite_risk
            orbit_map = {
                "geostationary": SatelliteOrbit.GEO,
                "l1": SatelliteOrbit.L1,
                "leo": SatelliteOrbit.LEO,
                "meo": SatelliteOrbit.MEO,
            }
            orbit_str = radiation_cfg.get("satellite_orbit", "geostationary")
            orbit = orbit_map.get(orbit_str.lower(), SatelliteOrbit.GEO)
            sep_indices = predictions["sep_risk_index"].values
            results = []
            for i in range(len(predictions)):
                result = assess_satellite_risk(
                    float(sep_indices[i]) if i < len(sep_indices) else 0.0,
                    orbit=orbit,
                )
                results.append(result.to_dict())
            for col in ["risk_level", "cumulative_dose_rate", "radiation_context", "advisory"]:
                predictions[f"sat_{col}"] = [r[col] for r in results]

    except Exception:
        predictions["sep_risk_context"] = predictions.apply(_sep_context_fallback, axis=1)
        return predictions

    return predictions


def _sep_context_fallback(row: pd.Series) -> str:
    klass = str(row.get("upcoming_flare_class", ""))[:1].upper()
    if klass in {"X", "M"} and row["flare_probability"] >= 0.55:
        return "Future-facing radiation watch: monitor SEP-capable data sources."
    if row.get("anomaly_index", 0) >= 65:
        return "Future-facing radiation context: anomalous behavior deserves analyst review."
    return "No validated SEP warning; panel is contextual only."


def write_reports(root: Path, dataset: pd.DataFrame, events: pd.DataFrame, predictions: pd.DataFrame, bundle, config: dict | None = None) -> None:
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    bundle.metrics.to_csv(reports / "metrics.csv", index=False)
    (reports / "feature_report.md").write_text(_feature_report(dataset), encoding="utf-8")
    (reports / "evaluation_report.md").write_text(_evaluation_report(bundle.metrics, predictions), encoding="utf-8")
    (reports / "mvp_to_final_development_plan.md").write_text(_final_version_plan(), encoding="utf-8")
    event_summary = build_event_summary(predictions, events)
    event_summary.to_csv(reports / "event_summary.csv", index=False)
    (reports / "event_summary.md").write_text(_event_summary_markdown(event_summary), encoding="utf-8")
    data_mode = predictions["data_mode"].iloc[0] if "data_mode" in predictions.columns else "synthetic_proxy_replay"
    soft_src = predictions["soft_source"].iloc[0] if "soft_source" in predictions.columns else "SYNTHETIC"
    hard_src = predictions["hard_source"].iloc[0] if "hard_source" in predictions.columns else "NONE"
    mission_mode = config.get("data", {}).get("mode", "synthetic") if config else "synthetic"
    staleness_info = compute_staleness_score(dataset) if config is not None else {"score": 0, "is_stale": False}
    manifest = build_artifact_manifest(
        root, dataset, predictions, bundle.metrics, event_summary,
        data_mode=data_mode, soft_source=soft_src, hard_source=hard_src,
        mission_mode=mission_mode, staleness=staleness_info,
    )
    (reports / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    top_features = sorted(bundle.final_model.feature_importance_.items(), key=lambda item: item[1], reverse=True)[:8]
    (reports / "top_features.json").write_text(json.dumps(top_features, indent=2), encoding="utf-8")
    mclass = dataset[dataset["scenario"].eq("M-class warning replay")] if "scenario" in dataset.columns and dataset["scenario"].eq("M-class warning replay").any() else None
    attention = bundle.final_model.attention_matrix(mclass if mclass is not None else dataset.head(200))
    attention.to_csv(reports / "attention_matrix.csv", index=False)
    events.to_csv(reports / "demo_events.csv", index=False)

    if config is not None:
        try:
            from arkanetra.evaluation import attention_heatmap as save_attention_heatmap
            save_attention_heatmap(attention, reports / "attention_heatmap.png", title="Cross-Attention Weights")
        except Exception:
            pass

        try:
            from arkanetra.evaluation import run_full_evaluation
            eval_results = run_full_evaluation(dataset, predictions, config, output_dir=reports)
            (reports / "comprehensive_evaluation.json").write_text(json.dumps(eval_results, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

        _write_alerts_and_audit(root, predictions, config, mission_mode)

    _write_predictions_jsonl(reports, predictions)


def build_event_summary(predictions: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Summarize replay scenarios for judge-facing inspection."""
    rows = []
    scenario_order = [
        "Quiet Sun replay",
        "C-class watch replay",
        "M-class warning replay",
        "X-class critical replay",
        "Background archive",
    ]
    for scenario in scenario_order:
        subset = predictions[predictions["scenario"] == scenario]
        if subset.empty:
            continue
        warning_subset = subset[subset["mission_state"].isin(["WARNING", "CRITICAL"])]
        first_warning = ""
        if not warning_subset.empty:
            first_warning = str(warning_subset.iloc[0]["timestamp"])
        event_id = ""
        flare_class = ""
        median_lead = np.nan
        labeled = warning_subset["time_to_flare_minutes"].dropna()
        if not labeled.empty:
            median_lead = float(labeled.median())
            event_id = str(warning_subset["upcoming_event_id"].dropna().astype(str).replace("", np.nan).dropna().iloc[0])
            flare_class = str(warning_subset["upcoming_flare_class"].dropna().astype(str).replace("", np.nan).dropna().iloc[0])
        rows.append(
            {
                "scenario": scenario,
                "event_id": event_id,
                "flare_class": flare_class,
                "rows": int(len(subset)),
                "max_probability": float(subset["flare_probability"].max()),
                "max_anomaly_index": float(subset["anomaly_index"].max()),
                "highest_state": _highest_state(subset["mission_state"]),
                "first_warning_timestamp": first_warning,
                "median_warning_lead_minutes": median_lead,
            }
        )
    return pd.DataFrame(rows)


def _highest_state(states: pd.Series) -> str:
    rank = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
    return max(states.astype(str), key=lambda state: rank.get(state, -1))


def _event_summary_markdown(summary: pd.DataFrame) -> str:
    return "# ArkaNetra Event Summary\n\n" + _markdown_table(summary) + "\n"


def build_artifact_manifest(
    root: Path,
    dataset: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    event_summary: pd.DataFrame,
    data_mode: str = "synthetic_proxy_replay",
    soft_source: str = "SYNTHETIC",
    hard_source: str = "NONE",
    mission_mode: str = "synthetic",
    staleness: dict | None = None,
) -> dict:
    """Build a compact evidence manifest for the MVP package."""
    paths = [
        "data/processed/arkanetra_mvp_dataset.parquet",
        "reports/predictions/arkanetra_mvp_predictions.parquet",
        "reports/metrics.csv",
        "reports/evaluation_report.md",
        "reports/event_summary.csv",
        "reports/event_summary.md",
        "reports/top_features.json",
        "reports/attention_matrix.csv",
        "docs/DOC-001_ArkaNetra_Constitution_v1.0.md",
        "docs/DOC-601_MVP_to_Final_Version_Development_Plan.md",
    ]
    artifact_paths = {}
    for relative in paths:
        path = root / relative
        artifact_paths[relative] = {"exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}
    best_model = metrics.sort_values("f1", ascending=False).iloc[0].to_dict()

    if mission_mode == "aditya_l1":
        limitations = [
            "Aditya-L1 mission data mode; operational performance not yet validated.",
            "Not an operational forecast.",
            "PyTorch GRU architecture is scaffolded but not required for the current runtime.",
        ]
    elif mission_mode == "goes_proxy":
        limitations = [
            "GOES proxy data used; operational performance based on proxy data.",
            "Not an operational forecast.",
            "PyTorch GRU architecture is scaffolded but not required for the current runtime.",
        ]
    else:
        limitations = [
            "Synthetic proxy replay data is used for immediate runnable MVP validation.",
            "Not an operational forecast.",
            "PyTorch GRU architecture is scaffolded but not required for the current runtime.",
        ]

    return {
        "project": "ArkaNetra",
        "mvp_version": "mvp-0.1",
        "data_mode": data_mode,
        "mission_mode": mission_mode,
        "soft_source": soft_source,
        "hard_source": hard_source,
        "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
        "dataset_rows": int(len(dataset)),
        "prediction_rows": int(len(predictions)),
        "scenarios": list(event_summary["scenario"]),
        "mission_states": predictions["mission_state"].value_counts().to_dict(),
        "staleness": staleness or {"score": 0, "is_stale": False},
        "best_model": best_model,
        "limitations": limitations,
        "artifacts": artifact_paths,
    }


def _feature_report(dataset: pd.DataFrame) -> str:
    lines = [
        "# ArkaNetra Feature Report",
        "",
        "Generated by the MVP pipeline.",
        "",
        "| Feature | Mean | Std | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for column in FEATURE_COLUMNS:
        series = dataset[column]
        lines.append(f"| {column} | {series.mean():.6g} | {series.std():.6g} | {series.min():.6g} | {series.max():.6g} |")
    return "\n".join(lines) + "\n"


def _evaluation_report(metrics: pd.DataFrame, predictions: pd.DataFrame) -> str:
    best = metrics.sort_values("f1", ascending=False).iloc[0]
    warning_rows = predictions[predictions["mission_state"].isin(["WARNING", "CRITICAL"])]
    lead = warning_rows["time_to_flare_minutes"].dropna()
    lead_text = "No lead-time rows available."
    if not lead.empty:
        lead_text = (
            f"Median warning lead time on labeled warning rows: {lead.median():.1f} minutes. "
            f"Range: {lead.min():.1f} - {lead.max():.1f} minutes."
        )
    metric_table = _markdown_table(metrics)
    lines = [
        "# ArkaNetra MVP Evaluation Report\n",
        "## Baseline And Model Comparison\n",
        f"{metric_table}\n",
        "## Current Best MVP Model\n",
        f"The highest F1 row is `{best['model']}` with F1={best['f1']:.3f}, "
        f"precision={best['precision']:.3f}, recall={best['recall']:.3f}.\n",
    ]
    if "brier_score" in best.index:
        lines.append(f"**Brier Score**: {best['brier_score']:.4f} (lower is better)\n")
    if "ece" in best.index:
        lines.append(f"**ECE**: {best['ece']:.4f} (lower is better)\n")
    if "false_alarm_rate" in best.index:
        lines.append(f"**False Alarm Rate**: {best['false_alarm_rate']:.4f}\n")
    lines.extend([
        "## Lead-Time Check\n",
        f"{lead_text}\n",
        "## Limitations\n",
        "This MVP uses deterministic synthetic proxy data to make the full pipeline runnable immediately. "
        "Real GOES/RHESSI/Fermi data adapters are scaffolded, and the final-version plan covers mission-data integration.\n",
    ])
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.4g}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _write_alerts_and_audit(root: Path, predictions: pd.DataFrame, config: dict, mission_mode: str) -> None:
    policy = config.get("alert_policy", {})
    alert_machine = AlertStateMachine(
        watch_probability=float(policy.get("watch_probability", 0.35)),
        warning_probability=float(policy.get("warning_probability", 0.55)),
        critical_probability=float(policy.get("critical_probability", 0.78)),
        anomaly_watch=float(policy.get("anomaly_watch", 45)),
        anomaly_supporting_warning=float(policy.get("anomaly_supporting_warning", 70)),
    )
    cfg_hash = compute_config_hash(config)
    ds_hash = compute_dataset_hash(predictions)
    alerts = alert_machine.generate_alerts(predictions, cfg_hash, ds_hash)
    alert_df = pd.DataFrame([a.to_dict() for a in alerts])
    alert_csv_path = root / "reports" / "alert_history.csv"
    alert_df.to_csv(alert_csv_path, index=False)
    alert_counts = alert_df["state"].value_counts().to_dict()
    write_audit_log(
        root, cfg_hash, ds_hash,
        config.get("project", {}).get("version", "unknown"),
        len(predictions),
        list(predictions["scenario"].unique()),
        alert_counts,
        mission_mode,
    )


def _write_predictions_jsonl(reports: Path, predictions: pd.DataFrame) -> None:
    predictions_dir = reports / "predictions"
    predictions_dir.mkdir(exist_ok=True)
    jsonl_path = predictions_dir / "predictions.jsonl"
    records = []
    for _, row in predictions.iterrows():
        record = {
            "timestamp": str(row.get("timestamp", "")),
            "scenario": str(row.get("scenario", "")),
            "mission_state": str(row.get("mission_state", "")),
            "flare_probability": float(row.get("flare_probability", 0.0)),
            "confidence_low": float(row.get("confidence_low", 0.0)),
            "confidence_high": float(row.get("confidence_high", 1.0)),
            "uncertainty_variance": float(row.get("uncertainty_variance", 0.0)),
            "anomaly_index": float(row.get("anomaly_index", 0.0)),
            "soft_xray_flux": float(row.get("soft_xray_flux", 0.0)),
            "hard_xray_flux": float(row.get("hard_xray_flux", 0.0)),
            "data_mode": str(row.get("data_mode", "")),
            "model_version": str(row.get("model_version", "")),
        }
        records.append(record)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def _final_version_plan() -> str:
    return """# ArkaNetra MVP To Final-Version Development Plan

## Version 1.1: Stronger Hackathon MVP

- Replace synthetic replay intervals with curated real GOES plus RHESSI/Fermi event windows.
- Add experiment tracking, exported event summaries, presentation-ready plots, and dashboard screenshots.
- Expand ablations across threshold baseline, soft-only model, multimodal model, and physics-loss variants.

## Version 1.5: Research Prototype

- Build a multi-year event dataset with chronological and event-based validation.
- Add multi-horizon prediction, severity classification, calibration, missing-data handling, and hyperparameter search.
- Prepare a technical report answering multimodal value, Neupert-loss value, anomaly-index timing, and uncertainty reliability.

## Version 2.0: Aditya-L1 Integration Prototype

- Add SoLEXS and HEL1OS ingestion adapters with payload metadata, cadence normalization, and data-quality checks.
- Keep proxy mode and Aditya-L1 mode in the same pipeline with explicit provenance in every prediction record.
- Update dashboard labels and explanations to be payload-aware.

## Version 2.5: Operational Decision-Support Prototype

- Add watch/warning/critical alert policy, threshold configuration, analyst notes, audit logs, and event summaries.
- Provide an API endpoint for prediction records and scenario comparison.
- Track model version, config, source data, and alert rationale for every warning.

## Version 3.0: Space-Weather Platform

- Add validated SEP-risk modeling with particle data and radiation-context workflows.
- Add satellite-risk and human-spaceflight mission context modules.
- Add forecast archive, subscription alerts, monitoring, drift checks, and continuous retraining.
"""


def run_mvp(config_path: str | Path | None = None) -> dict[str, Path]:
    config = load_config(config_path or ROOT / "configs" / "mvp.yaml")
    ensure_directories(ROOT)
    dataset, events = build_dataset(config)
    predictions, bundle = make_predictions(dataset, config, events)

    dataset_path = ROOT / "data" / "processed" / "arkanetra_mvp_dataset.parquet"
    prediction_path = ROOT / "reports" / "predictions" / "arkanetra_mvp_predictions.parquet"
    dataset.to_parquet(dataset_path, index=False)
    predictions.to_parquet(prediction_path, index=False)
    write_reports(ROOT, dataset, events, predictions, bundle, config)

    monitoring_path = _run_monitoring(predictions, bundle, config)

    return {
        "dataset": dataset_path,
        "predictions": prediction_path,
        "metrics": ROOT / "reports" / "metrics.csv",
        "monitoring": monitoring_path,
    }


def _run_monitoring(predictions, bundle, config) -> Path:
    monitoring_dir = ROOT / "reports" / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)

    try:
        from arkanetra.monitoring.orchestrator import MonitoringOrchestrator
        from arkanetra.monitoring.continuous_validation import ContinuousValidator
        from arkanetra.monitoring.status import generate_monitoring_dashboard, monitoring_dashboard_to_markdown

        archive = None
        monitoring_cfg = config.get("monitoring", {})
        archive_cfg = config.get("archive", {})
        if archive_cfg.get("enabled", False):
            from arkanetra.archive.forecast_archive import ForecastArchive
            archive = ForecastArchive(archive_path=ROOT / archive_cfg.get("path", "archive"))

        orchestrator = MonitoringOrchestrator(
            config=config,
            archive=archive,
            state_dir=ROOT / "monitoring",
        )

        best_metrics = bundle.metrics.sort_values("f1", ascending=False).iloc[0]
        validator = ContinuousValidator(
            baseline_f1=float(best_metrics["f1"]),
            baseline_roc_auc=float(best_metrics.get("roc_auc", 0.0)),
            state_dir=ROOT / "monitoring",
        )

        threshold = float(config["model"]["warning_threshold"])
        y_true = predictions["flare_label"].to_numpy()
        y_prob = predictions["flare_probability"].to_numpy()
        val_record = validator.validate(
            y_true, y_prob,
            model_version=config.get("project", {}).get("version", "unknown"),
            threshold=threshold,
        )

        cycle_result = orchestrator.run_cycle(
            current_predictions=predictions,
            reference_data=predictions,
        )

        dashboard = generate_monitoring_dashboard(orchestrator, validator)
        dashboard_md = monitoring_dashboard_to_markdown(dashboard)
        (monitoring_dir / "monitoring_dashboard.md").write_text(dashboard_md, encoding="utf-8")
        (monitoring_dir / "monitoring_dashboard.json").write_text(
            json.dumps(dashboard, indent=2, default=str), encoding="utf-8"
        )
        (monitoring_dir / "validation_report.md").write_text(validator.generate_report(), encoding="utf-8")
        (monitoring_dir / "orchestrator_report.md").write_text(orchestrator.generate_report(), encoding="utf-8")

        return monitoring_dir

    except Exception as e:
        (monitoring_dir / "monitoring_error.txt").write_text(f"Monitoring failed: {e}", encoding="utf-8")
        return monitoring_dir
