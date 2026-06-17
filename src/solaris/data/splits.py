from __future__ import annotations

import numpy as np
import pandas as pd


def add_chronological_split(frame: pd.DataFrame, train: float = 0.6, validation: float = 0.2) -> pd.DataFrame:
    """Assign chronological train/validation/test markers."""
    result = frame.sort_values("timestamp").reset_index(drop=True).copy()
    n = len(result)
    train_end = int(n * train)
    valid_end = int(n * (train + validation))
    result["split"] = "test"
    result.loc[: train_end - 1, "split"] = "train"
    result.loc[train_end: valid_end - 1, "split"] = "validation"
    return result


def add_event_based_split(
    frame: pd.DataFrame,
    train: float = 0.6,
    validation: float = 0.2,
    event_col: str = "upcoming_event_id",
    time_col: str = "timestamp",
    gap_minutes: float = 30.0,
) -> pd.DataFrame:
    """Split data by event groups to prevent temporal leakage.

    All rows belonging to the same event stay in the same split.
    A temporal gap is enforced between train and validation/test to prevent
    information leakage from overlapping event windows.

    Args:
        frame: Labeled dataset with event IDs and timestamps.
        train: Fraction of events for training.
        validation: Fraction of events for validation (remainder is test).
        event_col: Column containing event identifiers (NaN for quiet-Sun).
        time_col: Column containing timestamps.
        gap_minutes: Minimum temporal gap between train and validation sets in minutes.

    Returns:
        DataFrame with 'split' column assigned.
    """
    result = frame.sort_values(time_col).reset_index(drop=True).copy()
    result["split"] = "unassigned"

    has_event = result[event_col].notna() & (result[event_col] != "")
    event_ids = sorted(result.loc[has_event, event_col].unique())
    n_events = len(event_ids)

    if n_events == 0:
        n = len(result)
        train_end = int(n * train)
        valid_end = int(n * (train + validation))
        result["split"] = "test"
        result.loc[: train_end - 1, "split"] = "train"
        result.loc[train_end: valid_end - 1, "split"] = "validation"
        return result

    rng = np.random.default_rng(42)
    shuffled = list(event_ids)
    rng.shuffle(shuffled)
    n_train = max(1, int(n_events * train))
    n_valid = max(1, int(n_events * validation))
    train_events = set(shuffled[:n_train])
    valid_events = set(shuffled[n_train:n_train + n_valid])

    result.loc[has_event & result[event_col].isin(train_events), "split"] = "train"
    result.loc[has_event & result[event_col].isin(valid_events), "split"] = "validation"

    quiet = ~has_event
    quiet_idx = result.index[quiet]
    if len(quiet_idx) > 0:
        n_q = len(quiet_idx)
        q_train_end = int(n_q * train)
        q_valid_end = int(n_q * (train + validation))
        result.loc[quiet_idx[:q_train_end], "split"] = "train"
        result.loc[quiet_idx[q_train_end:q_valid_end], "split"] = "validation"

    unassigned = result["split"] == "unassigned"
    result.loc[unassigned, "split"] = "test"

    train_rows = result[result["split"] == "train"]
    valid_rows = result[result["split"].isin(["validation", "test"])]
    if not train_rows.empty and not valid_rows.empty:
        train_max = pd.to_datetime(train_rows[time_col]).max()
        valid_min = pd.to_datetime(valid_rows[time_col]).min()
        gap = (valid_min - train_max).total_seconds() / 60
        if gap < gap_minutes:
            cutoff = train_max + pd.Timedelta(minutes=gap_minutes)
            in_gap = (pd.to_datetime(result[time_col]) > train_max) & (pd.to_datetime(result[time_col]) < cutoff)
            result.loc[in_gap & (result["split"] == "test"), "split"] = "validation"

    return result

