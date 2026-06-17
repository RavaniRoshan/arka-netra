from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class ModelRegistry:
    def __init__(self, registry_path: Path | str | None = None):
        if registry_path is None:
            registry_path = Path("models/registry")
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.registry_path / "model_registry.json"
        self._index: dict = self._load_index()

    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                return {"models": [], "version": "1.0"}
        return {"models": [], "version": "1.0"}

    def _save_index(self):
        self.index_path.write_text(json.dumps(self._index, indent=2, default=str), encoding="utf-8")

    def register(
        self,
        model_version: str,
        model_state: dict | None = None,
        checkpoint_path: Path | None = None,
        metrics: pd.DataFrame | dict | None = None,
        config_snapshot: dict | None = None,
        data_source: str | None = None,
        architecture: str = "sklearn",
        notes: str = "",
    ) -> str:
        if model_version in [m.get("version") for m in self._index["models"]]:
            return self.update(model_version, model_state=model_state, metrics=metrics, notes=notes)

        version_dir = self.registry_path / model_version
        version_dir.mkdir(exist_ok=True)

        if checkpoint_path and checkpoint_path.exists():
            dest = version_dir / "model_checkpoint.pt"
            shutil.copy2(checkpoint_path, dest)

        if config_snapshot is not None:
            (version_dir / "config_snapshot.json").write_text(
                json.dumps(config_snapshot, indent=2, default=str), encoding="utf-8"
            )

        if metrics is not None:
            if isinstance(metrics, pd.DataFrame):
                metrics_dict = metrics.to_dict(orient="records")
            else:
                metrics_dict = metrics
            (version_dir / "metrics.json").write_text(
                json.dumps(metrics_dict, indent=2, default=str), encoding="utf-8"
            )

        best_f1 = None
        if isinstance(metrics, pd.DataFrame) and "f1" in metrics.columns:
            best_f1 = float(metrics["f1"].max())
        elif isinstance(metrics, dict) and "f1" in metrics:
            best_f1 = float(metrics["f1"])

        entry = {
            "version": model_version,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "data_source": data_source,
            "architecture": architecture,
            "best_f1": best_f1,
            "notes": notes,
            "path": str(version_dir),
        }
        self._index["models"].append(entry)
        self._save_index()
        return model_version

    def update(
        self,
        model_version: str,
        model_state: dict | None = None,
        metrics: pd.DataFrame | dict | None = None,
        notes: str = "",
    ) -> str:
        for entry in self._index["models"]:
            if entry["version"] == model_version:
                if metrics is not None:
                    if isinstance(metrics, pd.DataFrame):
                        metrics_dict = metrics.to_dict(orient="records")
                    else:
                        metrics_dict = metrics
                    version_dir = Path(entry["path"])
                    (version_dir / "metrics.json").write_text(
                        json.dumps(metrics_dict, indent=2, default=str), encoding="utf-8"
                    )
                    if "f1" in (metrics.columns if isinstance(metrics, pd.DataFrame) else metrics):
                        f1_col = metrics["f1"] if isinstance(metrics, pd.DataFrame) else metrics["f1"]
                        entry["best_f1"] = float(f1_col.max() if hasattr(f1_col, "max") else f1_col)
                if notes:
                    entry["notes"] = notes
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_index()
                return model_version
        return self.register(model_version, model_state=model_state, metrics=metrics, notes=notes)

    def list_models(self) -> list[dict]:
        return sorted(self._index["models"], key=lambda x: x.get("registered_at", ""), reverse=True)

    def get_latest(self) -> dict | None:
        models = self.list_models()
        return models[0] if models else None

    def get(self, version: str) -> dict | None:
        for entry in self._index["models"]:
            if entry["version"] == version:
                return entry
        return None

    def load_checkpoint_path(self, version: str) -> Path | None:
        entry = self.get(version)
        if entry is None:
            return None
        path = Path(entry["path"]) / "model_checkpoint.pt"
        return path if path.exists() else None

    def load_config_snapshot(self, version: str) -> dict | None:
        entry = self.get(version)
        if entry is None:
            return None
        path = Path(entry["path"]) / "config_snapshot.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None


_registry_instance: ModelRegistry | None = None


def get_registry(registry_path: Path | str | None = None) -> ModelRegistry:
    global _registry_instance
    if _registry_instance is None or registry_path is not None:
        _registry_instance = ModelRegistry(registry_path)
    return _registry_instance