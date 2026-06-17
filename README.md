# ArkaNetra

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
- **Phase 1**: Real GOES XRS soft X-ray integration (fixed SWPC URL, download.py, Fermi GBM, source labels, 10 new tests)
- **Phase 2**: PyTorch Deep Learning Activation (26 new GRU tests, all passing)
- **Phase 3**: Comprehensive Scientific Evaluation (32 new tests, Brier score, ECE, false alarm rate, lead-time analysis, SHAP explanations, cross-calibration)
- **Phase 4**: Monitoring & Continuous Retraining (34 new tests, drift detection, retrain triggers, validation, orchestrator)
- **Phase 5**: SEP & Radiation Risk Extension (38 new tests, human spaceflight dose estimation, satellite risk for all 4 orbits)
- **Phase 6**: Operational Platform Hardening (24 new tests, API auth, rate limiting, validation, Docker fixes, CI/CD)
- **Phase 7**: Aditya-L1 Mission Integration (14 new tests, ISRO telemetry download, cross-calibration, native terminology)

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

- `data/processed/arkanetra_mvp_dataset.parquet`
- `reports/predictions/arkanetra_mvp_predictions.parquet`
- `reports/metrics.csv`
- `reports/evaluation_report.md`
- `reports/event_summary.md`
- `reports/artifact_manifest.json`
- `reports/mvp_to_final_development_plan.md`
- `reports/monitoring/` (Phase 4+5 monitoring reports)
- `reports/radiation/` (Phase 5 radiation reports)
- `reports/cross_calibration/` (Phase 7 cross-calibration reports)

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
- **Phase 4-7 verification reports**: DOC-704, DOC-705, DOC-706, DOC-707 document all phases.

## Important Limitation

The current MVP uses deterministic synthetic proxy data so the full system can run immediately in this empty workspace. It is not an operational forecast. The next milestone is replacing synthetic windows with curated GOES XRS plus RHESSI/Fermi data and then adding the full PyTorch Dual-Branch Cross-Attention GRU.
