from __future__ import annotations

from pathlib import Path

import pandas as pd


def compute_staleness_score(
    dataset: pd.DataFrame,
    max_age_hours: int = 48,
    min_quality_fraction: float = 0.8,
) -> dict:
    """
    Compute staleness score for a dataset.
    Returns a dict with scores 0-100 (higher = more stale).
    """
    score = 0.0
    factors = {}

    if len(dataset) == 0:
        return {"score": 100, "factors": {"empty": 100}, "is_stale": True, "details": {}}

    last_timestamp = dataset["timestamp"].max()
    if pd.notna(last_timestamp):
        age_hours = (pd.Timestamp.now("UTC") - last_timestamp).total_seconds() / 3600
        age_score = min(100, (age_hours / max_age_hours) * 100)
        factors["age_hours"] = age_hours
        score += age_score * 0.4
        factors["age_score"] = age_score

    if "data_quality" in dataset.columns:
        valid_fraction = (dataset["data_quality"].isin(["ok", "stale"])).mean()
        quality_score = max(0, (1.0 - valid_fraction) * 100)
        factors["quality_fraction"] = float(valid_fraction)
        factors["quality_score"] = quality_score
        score += quality_score * 0.4

    if "is_stale" in dataset.columns:
        stale_fraction = dataset["is_stale"].mean()
        stale_score = stale_fraction * 100
        factors["stale_fraction"] = float(stale_fraction)
        factors["stale_score"] = stale_score
        score += stale_score * 0.2

    total_score = min(100, score)
    is_stale = total_score >= 50

    return {
        "score": float(total_score),
        "factors": factors,
        "is_stale": is_stale,
        "details": {
            "last_timestamp": str(last_timestamp) if pd.notna(last_timestamp) else None,
            "rows": len(dataset),
            "age_hours": factors.get("age_hours", 0),
            "quality_fraction": factors.get("quality_fraction", 1.0),
        }
    }


def add_staleness_flags(dataset: pd.DataFrame, threshold: float = 50.0) -> pd.DataFrame:
    """Add is_stale flag to dataset based on staleness score."""
    staleness = compute_staleness_score(dataset)
    dataset = dataset.copy()
    dataset["staleness_score"] = staleness["score"]
    dataset["is_stale"] = staleness["is_stale"]
    return dataset


def detect_data_gaps(
    dataset: pd.DataFrame,
    expected_cadence_minutes: int = 5,
    max_gap_count: int = 3,
) -> dict:
    """Detect gaps in the data time series."""
    if len(dataset) < 2 or "timestamp" not in dataset.columns:
        return {"has_gaps": False, "gap_count": 0, "gaps": []}

    timestamps = dataset["timestamp"].sort_values()
    diffs = timestamps.diff().dt.total_seconds().div(60)

    expected = expected_cadence_minutes
    tolerance = expected * 2
    gaps = diffs[diffs > tolerance]

    gap_count = len(gaps)
    has_gaps = gap_count >= max_gap_count

    gap_details = []
    for idx in gaps.index:
        gap_minutes = diffs.loc[idx]
        gap_details.append({
            "index": int(idx),
            "gap_minutes": float(gap_minutes),
        })

    return {
        "has_gaps": has_gaps,
        "gap_count": gap_count,
        "gaps": gap_details,
        "max_gap_minutes": float(gaps.max()) if len(gaps) > 0 else 0.0,
    }