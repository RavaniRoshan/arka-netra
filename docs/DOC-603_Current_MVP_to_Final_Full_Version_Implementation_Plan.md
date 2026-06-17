# DOC-603: Current MVP To Final Full-Version Implementation Plan

Project Solaris: Physics-Informed Multi-Modal Solar Flare Early Warning System  
Source of truth: DOC-001 Project Solaris Constitution v1.0  
Current baseline: Milestone 1.1 Demo-Hardened MVP  
Date: 2026-06-16  

## Purpose

This document is the step-by-step implementation plan for taking Project Solaris from the current MVP state to the final full version described in DOC-001.

The current MVP is a replay-first, demo-hardened system. It already includes synthetic GOES/RHESSI-style proxy data, mandatory physics-inspired features, short-horizon flare labels, baseline models, a multimodal fusion surrogate, uncertainty output, anomaly index, Streamlit mission console, artifact manifest, event summary, verification script, and documentation spine.

The final full version is an Aditya-L1-aligned, physics-informed, explainable, multimodal solar flare early warning and space-weather decision-support platform. It must use real data, support mission-relevant workflows, produce trusted explanations and uncertainty, and preserve the operational narrative defined in the Constitution.

## Guiding Principles

1. Preserve DOC-001 as the canonical foundation.
2. Do not turn Solaris into a generic flare classifier.
3. Keep the core thesis visible: soft X-ray plus hard X-ray interaction contains useful precursor information.
4. Treat physics-informed learning, uncertainty, explainability, and anomaly detection as required system components.
5. Separate hackathon demo claims from operational claims.
6. Preserve one clean pipeline contract from data ingestion to dashboard output.
7. Every phase must produce verifiable artifacts.

## Current Status

The current implementation has reached Milestone 1.1.

Completed:

- Project scaffold and Python package.
- Config-driven MVP pipeline.
- Synthetic proxy replay data generator.
- Feature engineering for mandatory Solaris features.
- Chronological train, validation, and test split.
- Baselines and executable multimodal fusion surrogate.
- Monte Carlo-style uncertainty output.
- PCA reconstruction-based anomaly index surrogate.
- Streamlit mission dashboard.
- Event summary and artifact manifest.
- One-command MVP verifier.
- Documentation through DOC-602.

Current known limitations:

- Data is synthetic proxy replay data.
- Real GOES XRS ingestion is not yet active in the main pipeline.
- RHESSI/Fermi hard X-ray ingestion is scaffolded but not operational.
- PyTorch Dual-Branch Cross-Attention GRU is scaffolded but not the active model.
- GRU autoencoder is not yet the active anomaly model.
- SEP risk is contextual only and not validated.

## Phase 1: Real Soft X-Ray Proxy Integration

Goal: replace at least one synthetic replay event with real GOES XRS soft X-ray data while preserving the current pipeline and dashboard contract.

### Step 1.1: Define GOES Data Access Path

Tasks:

- Identify the public GOES XRS data source to use for MVP real-data integration.
- Document source URL, cadence, channels, units, file format, and known caveats.
- Add the source decision to DOC-002 Decision Log.
- Keep the existing synthetic generator as a test fixture.

Deliverables:

- GOES source note in `docs/`.
- Updated DOC-002 decision entry.
- Config option for `data.mode: synthetic` or `data.mode: goes_proxy`.

Acceptance criteria:

- A developer can identify where GOES data comes from.
- The project can still run in synthetic mode.

### Step 1.2: Implement GOES Ingestion Adapter

Tasks:

- Extend `solaris.data.goes` to load the selected GOES data format.
- Normalize timestamps to UTC.
- Map GOES channels into the Solaris soft X-ray schema.
- Add data-quality flags for missing, zero, stale, or invalid flux rows.
- Add tests for timestamp normalization and required columns.

Deliverables:

- Operational GOES ingestion module.
- Sample real GOES data file or documented download step.
- Unit tests for GOES parsing.

Acceptance criteria:

- GOES data can be loaded into a DataFrame with `timestamp` and `soft_xray_flux`.
- The build pipeline can use GOES data without changing dashboard code.

### Step 1.3: Curate First Real Event Replay

Tasks:

- Select one real flare event with a clean GOES XRS window.
- Build a replay interval around the event.
- Generate labels using NOAA flare timing.
- Export the event into the same prediction schema used by the current dashboard.

Deliverables:

- One real GOES replay scenario.
- Updated `reports/event_summary.md`.
- Updated `reports/artifact_manifest.json`.

Acceptance criteria:

- Dashboard includes one real GOES scenario.
- `scripts/verify_mvp.py` passes.
- Synthetic and real replay modes are clearly labeled.

## Phase 2: Hard X-Ray Proxy Integration

Goal: add a real hard X-ray proxy so Solaris becomes genuinely multimodal in public-data mode.

### Step 2.1: Choose Hard X-Ray Proxy Source

Tasks:

- Evaluate RHESSI and Fermi GBM feasibility for the selected real GOES event.
- Prefer RHESSI if data access and preprocessing are manageable.
- Use Fermi GBM if RHESSI blocks progress.
- Record the decision in DOC-002.

Deliverables:

- Hard X-ray proxy decision note.
- Updated config with selected hard X-ray source.

Acceptance criteria:

- The chosen hard X-ray proxy can produce time-aligned `hard_xray_flux`.
- The reason for choosing RHESSI or Fermi is documented.

### Step 2.2: Implement Hard X-Ray Adapter

Tasks:

- Extend `solaris.data.hard_xray_proxy`.
- Normalize hard X-ray timestamps to UTC.
- Resample or align the hard X-ray series to GOES cadence.
- Add quality flags for missing or low-confidence hard X-ray samples.
- Preserve source provenance in processed data.

Deliverables:

- Operational hard X-ray proxy ingestion module.
- Tests for required schema and alignment.

Acceptance criteria:

- Processed rows contain both `soft_xray_flux` and `hard_xray_flux`.
- Hardness ratio can be computed from real proxy data.
- Missing hard X-ray data is handled explicitly, not silently.

### Step 2.3: Rebuild Multimodal Real-Data Replay

Tasks:

- Generate a real-data replay using GOES plus hard X-ray proxy.
- Recompute all mandatory features.
- Re-run baselines and fusion surrogate.
- Update dashboard artifacts.

Deliverables:

- Real multimodal replay prediction file.
- Updated metrics and event summary.
- Updated evaluation report.

Acceptance criteria:

- Dashboard can show real soft and hard X-ray plots.
- Artifact manifest clearly states source data.
- Synthetic-only limitation is removed or narrowed.

## Phase 3: PyTorch ML Architecture Upgrade

Goal: replace the executable sklearn/numpy surrogate with the intended Dual-Branch Cross-Attention GRU architecture.

### Step 3.1: Add PyTorch Dependency Path

Tasks:

- Decide whether PyTorch is installed by default or optional.
- Update `pyproject.toml` or create an extra dependency group.
- Document setup command for the ML training environment.
- Keep non-PyTorch smoke tests usable.

Deliverables:

- Documented PyTorch setup path.
- Runtime check that gives a clear error if PyTorch is missing.

Acceptance criteria:

- Developers can install and run the PyTorch training path.
- Dashboard artifacts can still be consumed without PyTorch installed.

### Step 3.2: Implement Sequence Dataset Builder

Tasks:

- Convert processed rows into lookback windows.
- Split features into soft branch and hard branch tensors.
- Preserve label, event metadata, source metadata, and timestamp.
- Prevent future leakage in all sequence windows.

Deliverables:

- Sequence dataset module.
- Tests for window shape, label alignment, and no future leakage.

Acceptance criteria:

- A single training sample contains only historical lookback data.
- Labels point to future flare horizon only.

### Step 3.3: Train Dual-Branch Cross-Attention GRU

Tasks:

- Use the existing `DualBranchCrossAttentionGRU` as the model base.
- Train soft and hard GRU encoders.
- Fuse with cross-attention.
- Output flare probability.
- Save checkpoint, config, metrics, and model metadata.

Deliverables:

- Active PyTorch training script.
- Model checkpoint under `models/`.
- Metrics under `reports/`.

Acceptance criteria:

- PyTorch model trains end-to-end.
- Inference output matches the dashboard schema.
- PyTorch model is compared against current surrogate and baselines.

### Step 3.4: Add Neupert Physics Loss

Tasks:

- Use normalized `d(SXR)/dt` and hard X-ray flux.
- Add `prediction_loss + lambda * neupert_loss`.
- Make lambda config-driven.
- Run physics-loss off/on ablation.

Deliverables:

- Physics-loss training mode.
- Ablation report.

Acceptance criteria:

- Metrics report includes physics-loss comparison.
- Explanation report describes whether Neupert loss helped accuracy, robustness, or interpretability.

## Phase 4: Anomaly Detection Upgrade

Goal: replace PCA reconstruction surrogate with the Constitution-defined GRU autoencoder.

### Step 4.1: Build Quiet-Sun Training Dataset

Tasks:

- Define quiet/non-flare intervals.
- Exclude windows too close to labeled flares.
- Save quiet-training metadata.

Deliverables:

- Quiet-Sun dataset builder.
- Quiet interval summary.

Acceptance criteria:

- Quiet training samples are separated from flare windows.
- The rule for quiet data selection is documented.

### Step 4.2: Train GRU Autoencoder

Tasks:

- Implement GRU encoder-decoder reconstruction model.
- Train on quiet windows.
- Save reconstruction error distribution.
- Convert reconstruction error to anomaly index from 0 to 100.

Deliverables:

- GRU autoencoder training script.
- Saved anomaly model checkpoint.
- Updated prediction schema with GRU anomaly index.

Acceptance criteria:

- Quiet replay has low anomaly.
- Flare or unusual windows show elevated anomaly.
- Dashboard consumes anomaly index without interface changes.

## Phase 5: Evaluation And Scientific Validation

Goal: make Solaris defensible as a research-grade prototype, not just a working demo.

### Step 5.1: Expand Metrics

Tasks:

- Report precision, recall, F1, PR-AUC, ROC-AUC, and confusion matrix.
- Add Brier score and calibration curve.
- Add event-based lead-time analysis.
- Add false alarm rate and missed event count.

Deliverables:

- Updated evaluation report.
- Metrics CSV with all required fields.
- Calibration plot.

Acceptance criteria:

- Evaluation proves more than classification accuracy.
- Lead time is reported for replay events.

### Step 5.2: Run Required Ablations

Tasks:

- Threshold baseline.
- Soft-only model.
- Hard-only model.
- Simple concatenation multimodal model.
- Cross-attention multimodal model.
- Physics-loss off/on.
- Anomaly off/on as warning support.

Deliverables:

- Ablation table.
- Short interpretation report.

Acceptance criteria:

- The project can defend why multimodal fusion and physics-informed learning matter.

### Step 5.3: Add Explanation Evaluation

Tasks:

- Generate top feature attributions.
- Generate attention heatmaps for selected events.
- Show Neupert consistency diagnostic.
- Save explanation artifacts per replay scenario.

Deliverables:

- Explanation report.
- Event-specific figures.

Acceptance criteria:

- Every warning scenario has a human-readable explanation.
- Explanations refer to physical features, not only model internals.

## Phase 6: Dashboard Productization

Goal: turn the dashboard into a stronger mission-control style decision-support interface.

### Step 6.1: Add Dashboard Modes

Tasks:

- Keep replay mode.
- Add analysis mode for event deep dives.
- Add model comparison mode.
- Add evidence/limitations mode.

Deliverables:

- Dashboard navigation or tabs.
- Scenario-specific analysis panels.

Acceptance criteria:

- A judge can understand the mission state in under one minute.
- A technical reviewer can inspect features, attention, anomaly, and uncertainty.

### Step 6.2: Add Event Summary Export

Tasks:

- Export event summary as Markdown and CSV.
- Optionally export PDF later.
- Include probability peak, anomaly peak, first warning time, lead time, top drivers, and source provenance.

Deliverables:

- Event summary export command.
- Updated report artifacts.

Acceptance criteria:

- Every replay scenario has a compact event report.

### Step 6.3: Add Alert Policy Configuration

Tasks:

- Keep watch, warning, and critical thresholds in config.
- Add uncertainty-aware state logic.
- Add stale-data or missing-data warning state.

Deliverables:

- Alert policy module.
- Tests for alert-state transitions.

Acceptance criteria:

- Alert states are reproducible from config.
- No alert is created without traceable inputs.

## Phase 7: Aditya-L1 Integration Prototype

Goal: transition from public proxy data to the future SoLEXS + HEL1OS mission identity.

### Step 7.1: Add SoLEXS Adapter

Tasks:

- Define SoLEXS expected schema.
- Map SoLEXS channels into Solaris soft X-ray features.
- Preserve payload metadata and quality flags.
- Add source provenance to every row.

Deliverables:

- SoLEXS ingestion module.
- SoLEXS schema documentation.

Acceptance criteria:

- SoLEXS data can enter the same feature pipeline as GOES.

### Step 7.2: Add HEL1OS Adapter

Tasks:

- Define HEL1OS expected schema.
- Map high-energy channels into hard X-ray features.
- Handle cadence, energy bands, and data gaps.
- Preserve payload metadata.

Deliverables:

- HEL1OS ingestion module.
- HEL1OS schema documentation.

Acceptance criteria:

- HEL1OS data can enter the same hard X-ray feature pipeline as RHESSI/Fermi proxy data.

### Step 7.3: Add Proxy Mode And Aditya-L1 Mode

Tasks:

- Add config mode switch: `proxy` or `aditya_l1`.
- Keep one prediction schema.
- Add dashboard source labels.
- Add data provenance panel.

Deliverables:

- Unified data-source abstraction.
- Payload-aware dashboard.

Acceptance criteria:

- The same dashboard can display proxy runs and Aditya-L1 runs.
- Users can clearly see which data source produced each prediction.

## Phase 8: Operational Decision-Support Prototype

Goal: move Solaris from research/demo into an analyst workflow.

### Step 8.1: Add Alert Lifecycle

Tasks:

- Define watch, warning, critical, resolved, and uncertain states.
- Add alert IDs.
- Add event start, peak, end, and update timestamps.
- Add operator notes.

Deliverables:

- Alert schema.
- Alert history report.

Acceptance criteria:

- Every alert is auditable.
- Alert transitions are reproducible.

### Step 8.2: Add Audit And Provenance

Tasks:

- Record model version, config hash, source data hash, generated time, and threshold policy.
- Save audit log for every prediction batch.
- Add dashboard audit viewer.

Deliverables:

- Audit log.
- Provenance metadata files.

Acceptance criteria:

- Every prediction can be traced to data, model, config, and code version.

### Step 8.3: Add Prediction API Or Service Contract

Tasks:

- Define JSON prediction output contract.
- Add optional FastAPI service or file-based API.
- Keep Streamlit as a consumer, not the owner of inference.

Deliverables:

- Prediction API contract.
- API smoke test.

Acceptance criteria:

- Another system can consume Solaris prediction records.

## Phase 9: SEP And Radiation Risk Extension

Goal: responsibly extend Solaris toward radiation-risk context without unsupported claims.

### Step 9.1: Define SEP Scope

Tasks:

- Document what SEP forecasting requires.
- Identify particle data sources.
- Separate flare warning from SEP risk.
- Update risk register.

Deliverables:

- SEP scope document.
- Updated DOC-403 risk register.

Acceptance criteria:

- The system does not claim validated SEP forecasting before particle-data validation.

### Step 9.2: Add Experimental SEP Risk Module

Tasks:

- Use flare severity, hard X-ray behavior, uncertainty, event history, and particle data when available.
- Output experimental SEP risk separately from flare risk.
- Mark output as experimental until validated.

Deliverables:

- SEP risk module.
- SEP evaluation plan.

Acceptance criteria:

- SEP panel is scientifically honest and clearly separated from flare prediction.

## Phase 10: Final Full-Version Platform

Goal: produce a complete Solaris platform suitable for research collaboration, operational pilot discussion, and future expansion.

### Step 10.1: System Hardening

Tasks:

- Add monitoring for failed ingestion, stale data, missing channels, and model drift.
- Add scheduled retraining workflow.
- Add model registry.
- Add release process.

Deliverables:

- Operating handbook.
- Release checklist.
- Model registry metadata.

Acceptance criteria:

- The system can be operated and updated without losing traceability.

### Step 10.2: Documentation Completion

Tasks:

- Complete DOC-201 through DOC-304.
- Complete DOC-401 through DOC-403.
- Complete DOC-501 through DOC-503.
- Keep DOC-001 aligned as the foundation.

Deliverables:

- Complete documentation hierarchy.
- Updated decision log.

Acceptance criteria:

- A new team can rebuild and defend Solaris from the documentation set.

### Step 10.3: Final Validation Package

Tasks:

- Run full evaluation on real proxy data.
- Run Aditya-L1 mode if data is available.
- Generate final demo script.
- Generate final presentation.
- Generate final technical report.

Deliverables:

- Final evaluation report.
- Final dashboard build.
- Final presentation package.
- Final defense handbook.

Acceptance criteria:

- Solaris demonstrates flare risk, uncertainty, explanation, anomaly detection, and mission relevance.
- Limitations are explicit.
- Claims are backed by evidence.

## Final Full-Version Definition Of Done

The final full version is complete only when all of the following are true:

- Real proxy data pipeline works end-to-end.
- Aditya-L1 SoLEXS and HEL1OS adapters are implemented or clearly mocked with exact schemas.
- Dual-Branch Cross-Attention GRU is the active model path.
- Neupert physics loss is implemented and evaluated.
- GRU autoencoder anomaly detection is active.
- Monte Carlo Dropout or equivalent uncertainty is active.
- Dashboard supports replay and analysis workflows.
- Alerts are configurable and auditable.
- Evaluation includes baselines, ablations, calibration, lead time, and explanation artifacts.
- SEP/radiation context is clearly separated from validated flare prediction.
- Documentation hierarchy is complete enough for handoff.
- Every major claim is supported by generated evidence.

## Immediate Next Action

The next development action should be Phase 1.1: define and document the public GOES XRS data source, then implement the first real GOES replay while preserving the current MVP contract.

