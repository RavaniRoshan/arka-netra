from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import shap as shap_lib
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


def _safe_auc(metric, y_true, y_score) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(metric(y_true, y_score))


def _brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(brier_score_loss(y_true, y_prob))


def _expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += mask.sum() / len(y_true) * abs(bin_acc - bin_conf)
    return float(ece)


def _calibration_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> tuple[np.ndarray, np.ndarray]:
    bin_edges = np.linspace(0, 1, n_bins + 1)
    mean_probs = []
    mean_true = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        mean_probs.append(y_prob[mask].mean())
        mean_true.append(y_true[mask].mean())
    return np.array(mean_probs), np.array(mean_true)


def _false_alarm_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    denom = fp + tn
    if denom == 0:
        return 0.0
    return float(fp / denom)


def comprehensive_metric_row(
    name: str,
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "pr_auc": _safe_auc(average_precision_score, y_true, y_score),
        "roc_auc": _safe_auc(roc_auc_score, y_true, y_score),
        "brier_score": _brier_score(y_true, y_score),
        "ece": _expected_calibration_error(y_true, y_score),
        "false_alarm_rate": _false_alarm_rate(y_true, y_pred),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
        "total_positives": int(y_true.sum()),
        "total_negatives": int((1 - y_true).sum()),
    }


def lead_time_analysis(
    predictions: pd.DataFrame,
    threshold: float,
    horizons: list[int] | None = None,
) -> dict:
    if horizons is None:
        horizons = [30, 60, 120]
    warning_rows = predictions[predictions["flare_probability"] >= threshold].copy()
    labeled = warning_rows["time_to_flare_minutes"].dropna()
    all_labeled = predictions["time_to_flare_minutes"].dropna()
    result: dict[str, Any] = {
        "n_warning_rows": int(len(warning_rows)),
        "n_labeled_warning_rows": int(len(labeled)),
        "median_lead_minutes": float(labeled.median()) if not labeled.empty else float("nan"),
        "mean_lead_minutes": float(labeled.mean()) if not labeled.empty else float("nan"),
        "min_lead_minutes": float(labeled.min()) if not labeled.empty else float("nan"),
        "max_lead_minutes": float(labeled.max()) if not labeled.empty else float("nan"),
        "std_lead_minutes": float(labeled.std()) if len(labeled) > 1 else 0.0,
        "percentile_25": float(labeled.quantile(0.25)) if not labeled.empty else float("nan"),
        "percentile_75": float(labeled.quantile(0.75)) if not labeled.empty else float("nan"),
    }
    for h in horizons:
        early = labeled[labeled <= h]
        result[f"fraction_within_{h}min"] = float(len(early) / len(all_labeled)) if len(all_labeled) > 0 else 0.0
        result[f"warnings_within_{h}min"] = int(len(early))
    return result


def false_alarm_analysis(y_true: np.ndarray, y_prob: np.ndarray, thresholds: list[float] | None = None) -> dict:
    if thresholds is None:
        thresholds = [0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8]
    rows = []
    for t in thresholds:
        y_pred = (y_prob >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        denom = fp + tn
        rows.append({
            "threshold": t,
            "false_alarm_rate": float(fp / denom) if denom > 0 else 0.0,
            "false_alarms": int(fp),
            "true_negatives": int(tn),
            "recall": float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0,
            "precision": float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0,
        })
    return {"thresholds": rows}


def ablation_study(
    dataset: pd.DataFrame,
    predictions: pd.DataFrame,
    config: dict,
) -> dict:
    from arkanetra.features import FEATURE_COLUMNS
    from arkanetra.models import ArkaNetraFusionModel

    threshold = float(config["model"]["warning_threshold"])
    y_true = predictions["flare_label"].to_numpy()
    y_prob = predictions["flare_probability"].to_numpy()
    train = dataset[dataset["split"] == "train"]
    valid = dataset[dataset["split"].isin(["validation", "test"])]
    y_valid = valid["flare_label"].to_numpy()

    results = {}

    full_scores = y_prob[valid.index] if len(valid) <= len(y_prob) else y_prob
    if len(full_scores) == len(y_valid):
        results["full_model"] = comprehensive_metric_row("full_model", y_valid, full_scores, threshold)

    soft_cols = ["soft_xray_flux", "soft_xray_derivative", "rolling_mean", "rolling_slope", "rolling_volatility"]
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    soft_only = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    y_train = train["flare_label"].to_numpy()
    soft_only.fit(train[soft_cols], y_train)
    soft_scores = soft_only.predict_proba(valid[soft_cols])[:, 1]
    results["soft_only"] = comprehensive_metric_row("soft_only", y_valid, soft_scores, threshold)

    hard_cols = ["hard_xray_flux", "hardness_ratio", "integrated_hard_xray_energy", "hard_rolling_slope"]
    hard_only = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    hard_only.fit(train[hard_cols], y_train)
    hard_scores = hard_only.predict_proba(valid[hard_cols])[:, 1]
    results["hard_only"] = comprehensive_metric_row("hard_only", y_valid, hard_scores, threshold)

    config_no_neupert = dict(config)
    config_no_neupert["model"] = dict(config["model"])
    config_no_neupert["model"]["neupert_lambda"] = 0.0
    model_no_np = ArkaNetraFusionModel(random_seed=42, neupert_lambda=0.0).fit(train)
    np_scores = model_no_np.predict_proba(valid)
    results["no_neupert"] = comprehensive_metric_row("no_neupert", y_valid, np_scores, threshold)

    model_with_np = ArkaNetraFusionModel(random_seed=42, neupert_lambda=float(config["model"]["neupert_lambda"])).fit(train)
    np_active_scores = model_with_np.predict_proba(valid)
    results["with_neupert"] = comprehensive_metric_row("with_neupert", y_valid, np_active_scores, threshold)

    results["physics_loss_comparison"] = {
        "neupert_lambda_off": results["no_neupert"]["f1"],
        "neupert_lambda_on": results["with_neupert"]["f1"],
        "f1_delta": results["with_neupert"]["f1"] - results["no_neupert"]["f1"],
    }

    return results


def attention_heatmap(
    attention_matrix: pd.DataFrame,
    output_path: Path,
    title: str = "Cross-Attention Heatmap",
) -> Path:
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for attention_heatmap()")
    fig, ax = plt.subplots(figsize=(8, 6))
    data = attention_matrix.values
    im = ax.imshow(data, aspect="auto", cmap="viridis", interpolation="nearest")
    ax.set_xlabel("Hard X-ray window")
    ax.set_ylabel("Soft derivative window")
    ax.set_title(title)
    plt.colorbar(im, ax=ax, label="Attention weight")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def calibration_plot(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    output_path: Path,
    model_name: str = "Model",
    n_bins: int = 10,
) -> Path:
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for calibration_plot()")
    mean_probs, mean_true = _calibration_curve(y_true, y_prob, n_bins)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfectly calibrated")
    ax.plot(mean_probs, mean_true, "s-", label=model_name)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def shap_explanations(
    model: Any,
    frame: pd.DataFrame,
    feature_columns: list[str],
    output_dir: Path,
    max_samples: int = 200,
) -> dict:
    if not HAS_SHAP:
        return {"available": False, "reason": "shap not installed"}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    x = frame[feature_columns].values
    feature_names = list(feature_columns)
    try:
        if hasattr(model, "classifier") and hasattr(model.classifier, "named_steps"):
            lr = model.classifier.named_steps["logisticregression"]
            scaler = model.classifier.named_steps["standardscaler"]
            x_scaled = scaler.transform(x)
            explainer = shap_lib.LinearExplainer(lr, x_scaled)
            shap_values = explainer.shap_values(x_scaled)
        elif hasattr(model, "classifier"):
            explainer = shap_lib.TreeExplainer(model.classifier)
            shap_values = explainer.shap_values(x)
        else:
            explainer = shap_lib.KernelExplainer(lambda data: model.predict_proba(pd.DataFrame(data, columns=feature_names)), shap_lib.sample(x, min(100, len(x))))
            shap_values = explainer.shap_values(x[:max_samples])
    except Exception as e:
        return {"available": False, "reason": str(e)}

    if HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(10, 6))
        if isinstance(shap_values, np.ndarray) and shap_values.ndim == 1:
            abs_vals = np.abs(shap_values)
        else:
            abs_vals = np.abs(np.array(shap_values)).mean(axis=0)
        sorted_idx = np.argsort(abs_vals)[::-1][:10]
        ax.barh([feature_names[i] for i in sorted_idx][::-1], abs_vals[sorted_idx][::-1])
        ax.set_xlabel("Mean |SHAP value|")
        ax.set_title("SHAP Feature Importance (Top 10)")
        fig.savefig(output_dir / "shap_summary.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    top_features = []
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
        abs_mean = np.abs(shap_values).mean(axis=0)
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 1:
        abs_mean = np.abs(shap_values)
    else:
        abs_mean = np.abs(np.array(shap_values)).mean(axis=0)
    sorted_idx = np.argsort(abs_mean)[::-1]
    for i in sorted_idx[:10]:
        top_features.append({"feature": feature_names[i], "importance": float(abs_mean[i])})
    (output_dir / "shap_top_features.json").write_text(json.dumps(top_features, indent=2), encoding="utf-8")
    return {"available": True, "top_features": top_features, "shap_values_shape": list(np.array(shap_values).shape)}


def run_full_evaluation(
    dataset: pd.DataFrame,
    predictions: pd.DataFrame,
    config: dict,
    output_dir: Path | None = None,
) -> dict:
    if output_dir is None:
        output_dir = Path("reports")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    threshold = float(config["model"]["warning_threshold"])
    y_true = predictions["flare_label"].to_numpy()
    y_prob = predictions["flare_probability"].to_numpy()
    y_pred = (y_prob >= threshold).astype(int)

    results = {}

    results["classification_metrics"] = {
        "threshold": threshold,
        "brier_score": _brier_score(y_true, y_prob),
        "ece": _expected_calibration_error(y_true, y_prob),
        "false_alarm_rate": _false_alarm_rate(y_true, y_pred),
    }

    results["lead_time"] = lead_time_analysis(predictions, threshold)
    results["false_alarm_analysis"] = false_alarm_analysis(y_true, y_prob)

    results["ablation"] = ablation_study(dataset, predictions, config)

    if HAS_MATPLOTLIB:
        try:
            cal_path = calibration_plot(y_true, y_prob, output_dir / "calibration_curve.png", model_name="ArkaNetra Model")
            results["calibration_plot"] = str(cal_path)
        except Exception as e:
            results["calibration_plot"] = f"Error: {e}"

    try:
        from arkanetra.features import FEATURE_COLUMNS
        train = dataset[dataset["split"] == "train"]
        model = ArkaNetraFusionModel(random_seed=42, neupert_lambda=float(config["model"]["neupert_lambda"]))
        model.fit(train)
        shap_results = shap_explanations(model, dataset.head(300), FEATURE_COLUMNS, output_dir / "shap")
        results["shap"] = shap_results
    except Exception as e:
        results["shap"] = {"available": False, "reason": str(e)}

    report_text = _generate_evaluation_report(results, predictions, config)
    (output_dir / "comprehensive_evaluation_report.md").write_text(report_text, encoding="utf-8")
    results["report_path"] = str(output_dir / "comprehensive_evaluation_report.md")

    return results


def _generate_evaluation_report(results: dict, predictions: pd.DataFrame, config: dict) -> dict:
    lines = [
        "# ArkaNetra Comprehensive Evaluation Report",
        "",
        f"Generated by the comprehensive evaluation suite.",
        "",
    ]

    cm = results.get("classification_metrics", {})
    lines.append("## Classification Metrics")
    lines.append("")
    lines.append(f"- **Threshold**: {cm.get('threshold', 'N/A')}")
    lines.append(f"- **Brier Score**: {cm.get('brier_score', 'N/A'):.4f}")
    lines.append(f"- **ECE**: {cm.get('ece', 'N/A'):.4f}")
    lines.append(f"- **False Alarm Rate**: {cm.get('false_alarm_rate', 'N/A'):.4f}")
    lines.append("")

    lt = results.get("lead_time", {})
    lines.append("## Lead-Time Analysis")
    lines.append("")
    lines.append(f"- **Median Lead Time**: {lt.get('median_lead_minutes', 'N/A')} minutes")
    lines.append(f"- **Mean Lead Time**: {lt.get('mean_lead_minutes', 'N/A')} minutes")
    for key in ["fraction_within_30min", "fraction_within_60min", "fraction_within_120min"]:
        if key in lt:
            horizon = key.split("_")[-2]
            lines.append(f"- **Fraction within {horizon}**: {lt[key]:.2%}")
    lines.append("")

    abl = results.get("ablation", {})
    lines.append("## Ablation Study")
    lines.append("")
    lines.append("| Model | F1 | Precision | Recall | ROC-AUC | Brier Score | ECE |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for key in ["soft_only", "hard_only", "no_neupert", "with_neupert", "full_model"]:
        if key in abl:
            m = abl[key]
            lines.append(
                f"| {key} | {m['f1']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | "
                f"{m['roc_auc']:.4f} | {m['brier_score']:.4f} | {m['ece']:.4f} |"
            )
    lines.append("")

    plc = abl.get("physics_loss_comparison", {})
    if plc:
        lines.append("### Physics Loss Comparison")
        lines.append("")
        lines.append(f"- **Neupert Lambda=0 F1**: {plc.get('neupert_lambda_off', 'N/A'):.4f}")
        lines.append(f"- **Neupert Lambda={config.get('model', {}).get('neupert_lambda', 0.18)} F1**: {plc.get('neupert_lambda_on', 'N/A'):.4f}")
        lines.append(f"- **F1 Delta**: {plc.get('f1_delta', 'N/A'):.4f}")
        lines.append("")

    fa = results.get("false_alarm_analysis", {})
    if "thresholds" in fa:
        lines.append("## False Alarm Rate Analysis")
        lines.append("")
        lines.append("| Threshold | FAR | False Alarms | Recall | Precision |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in fa["thresholds"]:
            lines.append(f"| {row['threshold']} | {row['false_alarm_rate']:.4f} | {row['false_alarms']} | {row['recall']:.4f} | {row['precision']:.4f} |")
        lines.append("")

    shap_res = results.get("shap", {})
    if shap_res.get("available"):
        lines.append("## SHAP Explanations")
        lines.append("")
        lines.append("Top features by SHAP importance:")
        lines.append("")
        for feat in shap_res.get("top_features", [])[:5]:
            lines.append(f"- **{feat['feature']}**: {feat['importance']:.4f}")
        lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append("This evaluation is based on synthetic proxy data. Results should be validated on real GOES/RHESSI/Fermi data.")
    lines.append("")

    return "\n".join(lines)
