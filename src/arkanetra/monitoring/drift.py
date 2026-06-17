from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from arkanetra.features import FEATURE_COLUMNS


@dataclass
class DriftReport:
    drift_detected: bool
    drift_score: float
    drifted_features: list[str]
    max_drift_feature: str
    interpretation: str
    threshold: float


def _kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    p = np.clip(p, epsilon, 1.0)
    q = np.clip(q, epsilon, 1.0)
    return float(np.sum(p * np.log(p / q)))


def _wasserstein_distance(a: np.ndarray, b: np.ndarray) -> float:
    a = np.sort(a)
    b = np.sort(b)
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    a = a[:min_len]
    b = b[:min_len]
    return float(np.mean(np.abs(a - b)))


def compute_drift_score(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    features: list[str] | None = None,
    method: str = "wasserstein",
) -> dict[str, float]:
    if features is None:
        features = FEATURE_COLUMNS

    scores = {}
    for col in features:
        if col not in reference.columns or col not in current.columns:
            continue
        ref_vals = reference[col].dropna().to_numpy()
        curr_vals = current[col].dropna().to_numpy()
        if len(ref_vals) < 5 or len(curr_vals) < 5:
            continue

        ref_mean = np.mean(ref_vals)
        ref_std = np.std(ref_vals)
        curr_mean = np.mean(curr_vals)
        curr_std = np.std(curr_vals)

        if ref_std > 1e-12 and curr_std > 1e-12:
            if method == "wasserstein":
                scores[col] = _wasserstein_distance(ref_vals, curr_vals)
            elif method == "mean_shift":
                normalized_shift = abs(curr_mean - ref_mean) / ref_std
                scores[col] = float(normalized_shift)
            else:
                normalized_shift = abs(curr_mean - ref_mean) / ref_std
                scores[col] = float(normalized_shift)
        else:
            scores[col] = 0.0

    return scores


def detect_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    threshold: float = 0.15,
    features: list[str] | None = None,
    method: str = "wasserstein",
) -> DriftReport:
    if features is None:
        features = FEATURE_COLUMNS

    drift_scores = compute_drift_score(reference, current, features, method)

    if not drift_scores:
        return DriftReport(
            drift_detected=False,
            drift_score=0.0,
            drifted_features=[],
            max_drift_feature="",
            interpretation="Insufficient data for drift detection",
            threshold=threshold,
        )

    max_feature = max(drift_scores, key=drift_scores.get)
    max_score = drift_scores[max_feature]
    drifted_features = [f for f, s in drift_scores.items() if s > threshold]
    overall_drift = float(np.mean(list(drift_scores.values())))

    if max_score >= threshold:
        interpretation = f"Drift detected: {max_feature} shifted by {max_score:.3f} (threshold: {threshold})"
    else:
        interpretation = f"No significant drift. Max feature shift: {max_feature} = {max_score:.3f}"

    return DriftReport(
        drift_detected=max_score >= threshold,
        drift_score=overall_drift,
        drifted_features=drifted_features,
        max_drift_feature=max_feature,
        interpretation=interpretation,
        threshold=threshold,
    )


def detect_drift_from_archive(
    archive,
    reference_run_id: str | None = None,
    recent_run_count: int = 5,
    threshold: float = 0.15,
) -> DriftReport | None:
    runs = archive.list_runs(limit=recent_run_count + 1)
    if len(runs) < 2:
        return None

    if reference_run_id:
        reference_preds = archive.load_predictions(reference_run_id)
    else:
        reference_preds = archive.load_predictions(runs[-1]["run_id"])

    latest_preds = archive.load_predictions(runs[0]["run_id"])
    if reference_preds is None or latest_preds is None:
        return None

    return detect_drift(reference_preds, latest_preds, threshold=threshold)