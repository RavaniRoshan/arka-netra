from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def config_hash(config: dict) -> str:
    """Compute SHA-256 hash of config dict."""
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]


def data_hash(data_paths: list[Path] | None = None) -> str:
    """Compute hash of source data files. Returns 'none' if no paths."""
    if not data_paths:
        return "none"
    h = hashlib.sha256()
    for path in sorted(data_paths):
        if path.exists():
            content = path.read_bytes()
            h.update(content)
    return h.hexdigest()[:16]


def compute_dataset_hash(dataset: pd.DataFrame) -> str:
    """Compute hash of dataset content for provenance."""
    h = hashlib.sha256()
    h.update(str(len(dataset)).encode("utf-8"))
    h.update(str(list(dataset.columns)).encode("utf-8"))
    if len(dataset) > 0:
        sample = dataset.head(100).to_csv(index=False)
        h.update(sample.encode("utf-8"))
    return h.hexdigest()[:16]


def write_audit_log(
    root: Path,
    config_hash: str,
    data_hash: str,
    model_version: str,
    prediction_rows: int,
    scenarios: list[str],
    alert_counts: dict[str, int],
    mission_mode: str,
) -> Path:
    """Write audit log entry to append-only JSONL file."""
    import datetime
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "config_hash": config_hash,
        "data_hash": data_hash,
        "model_version": model_version,
        "prediction_rows": prediction_rows,
        "scenarios": scenarios,
        "alert_counts": alert_counts,
        "mission_mode": mission_mode,
    }
    audit_path = root / "reports" / "audit_log.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, indent=2) + "\n")
    return audit_path


def read_audit_log(root: Path) -> list[dict]:
    """Read all entries from audit log."""
    audit_path = root / "reports" / "audit_log.jsonl"
    if not audit_path.exists():
        return []
    entries = []
    with audit_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries