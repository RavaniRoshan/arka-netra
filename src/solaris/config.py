from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "mvp.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load the MVP YAML config."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_directories(root: Path = ROOT) -> None:
    """Create the stable workspace folders used by the MVP."""
    for relative in [
        "data/raw",
        "data/interim",
        "data/processed",
        "models",
        "reports/predictions",
        "reports/figures",
        "reports/demo",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)

