from __future__ import annotations

from arkanetra.pipeline import run_mvp


if __name__ == "__main__":
    outputs = run_mvp()
    for name, path in outputs.items():
        print(f"{name}: {path}")

