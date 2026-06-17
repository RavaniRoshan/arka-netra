from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class ForecastArchive:
    def __init__(self, archive_path: Path | str | None = None, max_runs: int = 100):
        if archive_path is None:
            archive_path = Path("archive")
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.max_runs = max_runs
        self.index_path = self.archive_path / "forecast_archive_index.json"
        self._index: dict = self._load_index()

    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                return {"runs": [], "version": "1.0"}
        return {"runs": [], "version": "1.0"}

    def _save_index(self):
        self.index_path.write_text(json.dumps(self._index, indent=2, default=str), encoding="utf-8")

    def append(
        self,
        predictions: pd.DataFrame,
        config: dict | None = None,
        metrics: pd.DataFrame | dict | None = None,
        bundle_summary: dict | None = None,
    ) -> str:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = self.archive_path / run_id
        run_dir.mkdir(exist_ok=True)

        predictions_path = run_dir / "predictions.parquet"
        predictions.to_parquet(predictions_path, index=True)

        if config is not None:
            (run_dir / "config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")

        if metrics is not None:
            if isinstance(metrics, pd.DataFrame):
                metrics_dict = metrics.to_dict(orient="records")
            else:
                metrics_dict = metrics
            (run_dir / "metrics.json").write_text(json.dumps(metrics_dict, indent=2, default=str), encoding="utf-8")

        if bundle_summary is not None:
            (run_dir / "bundle_summary.json").write_text(
                json.dumps(bundle_summary, indent=2, default=str), encoding="utf-8"
            )

        total_rows = len(predictions)
        best_f1 = None
        if isinstance(metrics, pd.DataFrame) and "f1" in metrics.columns:
            best_f1 = float(metrics["f1"].max())
        elif isinstance(metrics, dict):
            for m in metrics if isinstance(metrics, list) else [metrics]:
                if "f1" in m:
                    best_f1 = float(m["f1"])

        run_entry = {
            "run_id": run_id,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "predictions_path": str(predictions_path),
            "total_rows": total_rows,
            "best_f1": best_f1,
            "data_mode": config.get("data", {}).get("mode", "unknown") if config else "unknown",
            "architecture": config.get("model", {}).get("architecture", "unknown") if config else "unknown",
        }
        self._index["runs"].append(run_entry)
        self._enforce_retention()
        self._save_index()
        return run_id

    def _enforce_retention(self):
        if len(self._index["runs"]) > self.max_runs:
            runs_to_remove = self._index["runs"][:-self.max_runs]
            self._index["runs"] = self._index["runs"][-self.max_runs:]
            for run in runs_to_remove:
                run_dir = self.archive_path / run["run_id"]
                if run_dir.exists():
                    try:
                        import shutil
                        shutil.rmtree(run_dir)
                    except Exception:
                        pass

    def list_runs(self, limit: int | None = None) -> list[dict]:
        runs = sorted(self._index["runs"], key=lambda x: x.get("archived_at", ""), reverse=True)
        if limit is not None:
            runs = runs[:limit]
        return runs

    def get_run(self, run_id: str) -> dict | None:
        for run in self._index["runs"]:
            if run["run_id"] == run_id:
                return run
        return None

    def load_predictions(self, run_id: str) -> pd.DataFrame | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        path = Path(run["predictions_path"])
        if path.exists():
            return pd.read_parquet(path)
        return None

    def load_config(self, run_id: str) -> dict | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        run_dir = self.archive_path / run_id
        config_path = run_dir / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
        return None

    def get_latest_run(self) -> dict | None:
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None


_archive_instance: ForecastArchive | None = None


def append_forecast(
    predictions: pd.DataFrame,
    config: dict | None = None,
    metrics: pd.DataFrame | dict | None = None,
    bundle_summary: dict | None = None,
    archive_path: Path | str | None = None,
) -> str:
    global _archive_instance
    if _archive_instance is None or archive_path is not None:
        _archive_instance = ForecastArchive(archive_path)
    return _archive_instance.append(predictions, config, metrics, bundle_summary)