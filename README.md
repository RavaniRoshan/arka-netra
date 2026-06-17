# Project Solaris

Physics-informed multimodal solar flare early-warning MVP for ISRO Problem Statement #15.

## What Is Implemented

- Replay-first MVP scaffold.
- Synthetic GOES/RHESSI-style proxy data generator.
- Mandatory physics-inspired features.
- Short-horizon flare labels and chronological splits.
- Baselines plus executable multimodal fusion surrogate.
- Monte Carlo-style uncertainty.
- Anomaly index.
- Streamlit mission dashboard.
- Evaluation and development-roadmap reports.
- Event summary and artifact manifest for judge-facing inspection.

## Setup

Use the bundled Python runtime or any Python 3.11+ environment.

```powershell
python -m pip install -e .
```

## Build MVP Artifacts

```powershell
python scripts/build_mvp.py
```

Outputs:

- `data/processed/solaris_mvp_dataset.parquet`
- `reports/predictions/solaris_mvp_predictions.parquet`
- `reports/metrics.csv`
- `reports/evaluation_report.md`
- `reports/event_summary.md`
- `reports/artifact_manifest.json`
- `reports/mvp_to_final_development_plan.md`

## Run Dashboard

```powershell
streamlit run app/streamlit_app.py
```

## Run Tests

```powershell
pytest
```

## Verify MVP Package

```powershell
python scripts/verify_mvp.py
```

## Current MVP Evidence

- The dashboard provides four replay scenarios: quiet Sun, C-class watch, M-class warning, and X-class critical.
- `reports/event_summary.md` gives a compact scenario-by-scenario demo summary.
- `reports/artifact_manifest.json` records generated artifacts, dataset row counts, model metrics, and explicit limitations.
- `docs/DOC-601_MVP_to_Final_Version_Development_Plan.md` is the detailed path from this MVP to the final system.
- `docs/DOC-602_Milestone_1.1_Demo_Hardening_Report.md` records the current polished milestone.

## Important Limitation

The current MVP uses deterministic synthetic proxy data so the full system can run immediately in this empty workspace. It is not an operational forecast. The next milestone is replacing synthetic windows with curated GOES XRS plus RHESSI/Fermi data and then adding the full PyTorch Dual-Branch Cross-Attention GRU.
