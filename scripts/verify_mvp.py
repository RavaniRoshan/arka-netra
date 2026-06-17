from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        ROOT / "data" / "processed" / "arkanetra_mvp_dataset.parquet",
        ROOT / "reports" / "predictions" / "arkanetra_mvp_predictions.parquet",
        ROOT / "reports" / "metrics.csv",
        ROOT / "reports" / "event_summary.csv",
        ROOT / "reports" / "artifact_manifest.json",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("Missing required artifacts:")
        for path in missing:
            print(f"- {path}")
        return 1

    predictions = pd.read_parquet(ROOT / "reports" / "predictions" / "arkanetra_mvp_predictions.parquet")
    summary = pd.read_csv(ROOT / "reports" / "event_summary.csv")
    manifest = json.loads((ROOT / "reports" / "artifact_manifest.json").read_text(encoding="utf-8"))

    required_scenarios = {"Quiet Sun replay", "C-class watch replay", "M-class warning replay", "X-class critical replay"}
    actual_scenarios = set(summary["scenario"])
    if not required_scenarios.issubset(actual_scenarios):
        print(f"Scenario mismatch: expected {sorted(required_scenarios)}, found {sorted(actual_scenarios)}")
        return 1

    quiet = predictions[predictions["scenario"].eq("Quiet Sun replay")]
    if quiet.empty or not quiet["mission_state"].eq("NORMAL").all():
        print("Quiet Sun replay must exist and remain NORMAL for all rows.")
        return 1

    event_scenarios = predictions[predictions["scenario"].isin(["C-class watch replay", "M-class warning replay", "X-class critical replay"])]
    if event_scenarios["mission_state"].isin(["WARNING", "CRITICAL"]).sum() < 3:
        print("Event scenarios must produce warning or critical states.")
        return 1

    if manifest.get("prediction_rows") != len(predictions):
        print("Manifest prediction row count does not match saved predictions.")
        return 1

    print("ArkaNetra MVP verification passed.")
    print(f"Rows: {len(predictions)}")
    print(f"Scenarios: {', '.join(sorted(required_scenarios))}")
    print(f"Best model: {manifest['best_model']['model']} F1={manifest['best_model']['f1']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

