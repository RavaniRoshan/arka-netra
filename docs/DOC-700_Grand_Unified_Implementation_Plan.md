# DOC-700: Grand Unified Implementation Plan (GUIP)

Project: Project Solaris — Physics-Informed Multi-Modal Solar Flare Early Warning System
Prepared for: Bharatiya Antariksh Hackathon 2026, ISRO Problem Statement #15
Document status: Active master execution plan
Version: 1.0
Date: 2026-06-17

---

## Document Purpose

This is the master plan for taking Project Solaris from its current documented state to the full vision described in DOC-001 (Constitution). It consolidates all six phases, includes a complete document registry, a timeline, and serves as the single source of truth for execution order.

This document derives from DOC-001 (Constitution), inherits from DOC-601 (MVP-to-Final Plan), and validates against all Phase verification reports (DOC-602, DOC-608, DOC-610, DOC-613, DOC-614).

---

## Part I: Truth Audit — Current State as of 2026-06-17

### Tests

| Metric | Value |
|--------|-------|
| Total tests collected | 79 |
| Tests passed | 79 |
| Tests failed | 0 |
| Warnings | 7 (expected — SWPC API unreachable, missing sample files) |
| Test files | 9 |

Test distribution by module:
| Test File | Tests |
|-----------|-------|
| test_artifacts.py | 3 |
| test_features.py | 2 |
| test_goes_adapter.py | 9 |
| test_hard_xray_proxy.py | 10 |
| test_hel1os_adapter.py | 17 |
| test_models.py | 1 |
| test_pipeline.py | 2 |
| test_reliability.py | 19 |
| test_solexs_adapter.py | 16 |

### Active vs Scaffolded Components

| Component | Status | Notes |
|-----------|--------|-------|
| GOES XRS adapter (`goes.py`) | Active (bundled CSV) | Live SWPC JSON download returns 404 — bundled CSV fallback works |
| Hard X-ray proxy (`hard_xray_proxy.py`) | Scaffolded | CSV loader works; FITS download implemented but not validated in CI; no live Fermi GBM path |
| SoLEXS adapter (`solexs.py`) | Active (bundled CSV) | Works with `aditya_l1_sample` directory |
| HEL1OS adapter (`hel1os.py`) | Active (bundled CSV) | Works with `aditya_l1_sample` directory |
| Synthetic data (`synthetic.py`) | Active (deterministic) | The default data mode |
| sklearn model (`models.py`) | Active | LogisticRegression with feature importance; F1=0.893 on synthetic |
| PyTorch GRU (`torch_models.py`) | Scaffolded | DualBranchCrossAttentionGRU, GRUAutoencoder, SequenceDataset all defined but not the active training path |
| Training loop (`training.py`) | Scaffolded | `train_gru_model()` exists but not validated |
| Anomaly detection (`anomaly.py`) | Active (PCA) | PCA reconstruction is active; GRU autoencoder is scaffolded |
| Alert lifecycle (`alerts/`) | Active | AlertStateMachine, audit log, provenance tracking |
| Staleness (`staleness.py`) | Active | compute_staleness_score, data gap detection |
| Pipeline (`pipeline.py`) | Active | Full end-to-end with all three data modes |
| SEP risk (`radiation/`) | Scaffolded | Modules exist; marked experimental |
| FastAPI (`api/`) | Scaffolded | prediction_api.py exists |
| Model registry (`registry/`) | Scaffolded | model_registry.py exists |
| Forecast archive (`archive/`) | Scaffolded | forecast_archive.py exists |
| Dashboard (`app/streamlit_app.py`) | Active | Replay mode works; analysis, comparison, multi-horizon modes scaffolded |

### Data Files

| File | Status | Description |
|------|--------|-------------|
| data/processed/solaris_mvp_dataset.parquet | Present | MVP dataset from synthetic mode |
| data/raw/goes_sample/goes_xrs_20170905_20170907.csv | Present | GOES XRS 2017 Sep 5-7 (X9.3 event) |
| data/raw/goes_sample/rhessi_hard_xray_20170905_20170907.csv | Present | RHESSI hard X-ray for same period |
| data/raw/goes_sample/noaa_flare_catalog_20170906.csv | Present | NOAA flare catalog for 2017-09-06 |
| data/raw/aditya_l1_sample/solexs_sample_20260101_20260102.csv | Present | Synthetic SoLEXS sample |
| data/raw/aditya_l1_sample/hel1os_sample_20260101_20260102.csv | Present | Synthetic HEL1OS sample |
| data/raw/aditya_l1_sample/noaa_flare_catalog_solexs.csv | Present | Synthetic flare catalog for Aditya-L1 |

### Key Gaps (Verified)

1. **SWPC GOES live download**: Returns HTTP 404. The SWPC JSON API URL may need updating. Tests pass because fallback to bundled CSV works.
2. **No live Fermi GBM download path**: The `hard_xray_proxy.py` handles RHESSI CSV but has no GBM download logic.
3. **PyTorch GRU not validated**: Defined but not the active training/inference path.
4. **No real-data validation test**: Tests use synthetic or bundled CSV data; no test validates against live API data.
5. **No GRU-specific tests**: Despite `torch_models.py` being present, there are only 1 model test.
6. **Staleness tests are in reliability**: `test_reliability.py` covers staleness, but not with real data gaps.
7. **No Fermi GBM test**: `test_hard_xray_proxy.py` tests CSV loader and quality flags, nothing for GBM.

---

## Part II: Document Registry

All documents in the Project Solaris documentation hierarchy, indexed by creation order.

| DOC ID | Title | Date | Purpose |
|--------|-------|------|---------|
| DOC-001 | Project Solaris Constitution v1.0 | 2026-06-16 | Canonical foundation; defines mission, architecture, philosophy |
| DOC-002 | Decision Log | 2026-06-16 | All architectural decisions with rationale |
| DOC-401 | Hackathon Roadmap | 2026-06-16 | Hackathon-specific milestones and judging strategy |
| DOC-402 | Task Board | 2026-06-16 | Task tracking across all phases |
| DOC-403 | Risk Register | 2026-06-16 | Risk tracking with mitigations |
| DOC-501 | Judge Question Bank | 2026-06-16 | Anticipated judge questions and answers |
| DOC-502 | Technical Defense Handbook | 2026-06-16 | MVP architecture defense talking points |
| DOC-503 | Demo Script | 2026-06-16 | 10-step demo walkthrough |
| DOC-601 | MVP to Final-Version Development Plan | 2026-06-16 | Step-by-step roadmap from MVP to final |
| DOC-602 | Milestone 1.1 Demo Hardening Report | 2026-06-16 | MVP baseline verification |
| DOC-603 | Current MVP to Final Full-Version Implementation Plan | 2026-06-16 | Detailed phased implementation plan |
| DOC-603 | Phase 1 GOES Source Spec | 2026-06-16 | GOES XRS data source specification |
| DOC-604 | Phase 2 Hard X-ray SWOT | 2026-06-16 | RHESSI + Fermi GBM dual-source SWOT analysis |
| DOC-605 | Phase 3 Aditya-L1 Plan | 2026-06-16 | SoLEXS/HEL1OS integration prototype plan |
| DOC-606 | SoLEXS Schema | 2026-06-16 | SoLEXS instrument schema reference |
| DOC-607 | HEL1OS Schema | 2026-06-16 | HEL1OS instrument schema reference |
| DOC-608 | Phase 3 Verification Report | 2026-06-16 | Phase 3 exit criteria verification (60/60 tests) |
| DOC-610 | Phase 4 Verification Report | 2026-06-16 | Phase 4 exit criteria verification (alert lifecycle, API) |
| DOC-611 | Operating Handbook | 2026-06-16 | Full operating guide |
| DOC-612 | Publication Materials | 2026-06-16 | Technical report, model cards, API reference |
| DOC-613 | Phase 5 Verification Report | 2026-06-16 | Phase 5 exit criteria verification |
| DOC-614 | Phase 6 Verification Report | 2026-06-16 | Phase 6 exit criteria verification (79/79 tests) |
| **DOC-700** | **Grand Unified Implementation Plan (GUIP)** | **2026-06-17** | **Master execution plan; this document** |

---

## Part III: Phase Timeline

All dates reference the implementation period beginning 2026-06-17.

| Phase | Name | Start | Target Completion | Dependencies |
|-------|------|-------|-------------------|-------------|
| 0 | Truth Audit & Foundation | 2026-06-17 | 2026-06-17 | None |
| 1 | Real Data Ingestion Hardening | 2026-06-17 | 2026-06-17 | Phase 0 |
| 2 | PyTorch Deep Learning Activation | TBD | TBD | Phase 1 |
| 3 | Comprehensive Scientific Evaluation | TBD | TBD | Phase 2 |
| 4 | Dashboard Productization | TBD | TBD | Phase 3 |
| 5 | SEP & Radiation Risk Extension | TBD | TBD | Phase 4 |
| 6 | Operational Platform Hardening | TBD | TBD | Phase 5 |
| 7 | Aditya-L1 Mission Integration | TBD | TBD | Phase 6 |
| 8 | Continuous Research & Publication | TBD | TBD | Phase 7 |

---

## Part IV: Grand Phase Plan

### PHASE 0: Foundation & Truth Audit

**Goal**: Establish a rigorous, honest baseline before any expansion.

**Exit Criteria**:
- [ ] DOC-700 created (this document)
- [ ] Current test suite verified to pass (79/79)
- [ ] Gap analysis documented in Part I
- [ ] All scaffolded vs active components identified

---

### PHASE 1: Real Data Ingestion Hardening

**Goal**: Make all three data modes (`synthetic`, `goes_proxy`, `aditya_l1`) production-robust with validated live data download paths.

**Tasks**:
1. Fix GOES SWPC live JSON download (HTTP 404 issue)
2. Add Fermi GBM live download path to `hard_xray_proxy.py`
3. Implement retry logic for all network downloads
4. Add comprehensive connection error handling
5. Add data quality validation across all modes
6. Ensure all data provenance is tracked in audit logs
7. Add tests for live download paths (with graceful fallback)

**Exit Criteria**:
- [ ] GOES SWPC download works or has validated fallback
- [ ] Fermi GBM download path implemented
- [ ] All three data modes run end-to-end with verifiable provenance
- [ ] Retry and error handling tested for all network paths
- [ ] DOC-701 Phase 1 Verification Report written

---

### PHASE 2: PyTorch Deep Learning Activation

**Goal**: Transition from sklearn surrogate to validated physics-informed GRU.

**Tasks**:
1. Validate GRU `SequenceDataset` for no-future-leakage
2. Implement production-grade training loop with early stopping
3. Implement Neupert physics loss validation
4. Train and validate GRU autoencoder on quiet-Sun intervals
5. Replace PCA anomaly with GRU autoencoder as active path
6. Integrate ModelRegistry for GRU checkpointing
7. Add comprehensive GRU tests

**Exit Criteria**:
- [ ] GRU trains on real proxy data with stable loss
- [ ] Neupert loss ablation documented
- [ ] GRU autoencoder anomaly detection active
- [ ] ModelRegistry handles GRU save/load/rollback

---

### PHASE 3: Comprehensive Scientific Evaluation

**Goal**: Make Solaris defensible as a research prototype.

**Tasks**:
1. Implement event-based train/validation/test splits
2. Add Brier score, ECE, ROC-AUC, PR-AUC metrics
3. Add lead-time analysis, false alarm rate
4. Automate ablation studies (soft-only, hard-only, multimodal, physics-loss on/off)
5. Generate attention heatmaps and SHAP explanations
6. Create evaluation report generation

**Exit Criteria**:
- [ ] Full metrics suite documented
- [ ] Ablation table with soft-only, hard-only, multimodal, cross-attention
- [ ] Physics-loss on/off comparison
- [ ] Event-based splits prevent temporal leakage

---

### PHASE 4: Dashboard Productization & Analyst Workflow

**Goal**: Transform dashboard from demo to mission-control tool.

**Tasks**:
1. Deep-dive analysis mode (signals, features, attention, anomaly, Neupert)
2. Model comparison mode (sklearn vs GRU side-by-side)
3. Multi-horizon display (30min, 60min, 120min)
4. Event summary export (Markdown/CSV)
5. Threshold policy selector (Conservative/Balanced/Aggressive)

**Exit Criteria**:
- [ ] Judge can understand mission state in <1 minute
- [ ] Technical reviewer can inspect all model internals
- [ ] Event summaries exportable

---

### PHASE 5: SEP & Radiation Risk Extension

**Goal**: Add responsible mission-risk context.

**Tasks**:
1. Define validated SEP forecasting scope and disclaimer boundary
2. Expand satellite risk to GEO/LEO/MEO/L1 orbits
3. Add human spaceflight radiation dose estimation
4. Maintain experimental disclaimers on all radiation outputs

**Exit Criteria**:
- [ ] SEP module carries is_experimental disclaimers
- [ ] Satellite risk covers all orbit types
- [ ] No unsupported operational claims

---

### PHASE 6: Operational Platform Hardening

**Goal**: Prepare for operational pilot deployment.

**Tasks**:
1. Full alert lifecycle state machine (NORMAL→WATCH→WARNING→CRITICAL→RESOLVED)
2. Immutable audit logs
3. Production-grade FastAPI endpoints
4. Feature drift detection and retraining triggers
5. Docker, CI/CD, release tagging

**Exit Criteria**:
- [ ] Alert lifecycle fully auditable
- [ ] API handles auth, rate limiting, input validation
- [ ] Docker build produces working container
- [ ] CI runs lint + tests on push

---

### PHASE 7: Aditya-L1 Mission Integration

**Goal**: Transition from proxy to mission-native data.

**Tasks**:
1. Connect to ISRO telemetry feeds or archives
2. Cross-calibrate SoLEXS against GOES XRS
3. Cross-calibrate HEL1OS against RHESSI/Fermi
4. Dashboard terminology fully Aditya-L1 native

**Exit Criteria**:
- [ ] Live SoLEXS/HEL1OS pipelines operational
- [ ] Cross-calibration documented
- [ ] Dashboard shows Aditya-L1 source terminology

---

### PHASE 8: Continuous Research & Publication

**Goal**: Living research platform beyond hackathon.

**Tasks**:
1. Automated technical report generation
2. Model cards for every registered version
3. Curated dataset publication
4. Architecture exploration (Transformer, Mamba)

**Exit Criteria**:
- [ ] Automated report pipeline
- [ ] Model cards current
- [ ] Community benchmark release ready

---

## Part V: Execution Rules

1. **No Phase Skipping**: Each phase must complete all exit criteria before the next begins.
2. **Verification After Every Phase**: A verification report (DOC-701, DOC-702, etc.) is written for each completed phase.
3. **Tests Must Never Regress**: All 79 existing tests must continue passing.
4. **No Unsupported Claims**: Experimental features remain flagged as experimental.
5. **Constitution Alignment**: Every implementation decision must be traceable back to DOC-001.
6. **Phase Approval Gate**: After completing each phase, implementation pauses so the team can review and approve progression to the next phase.

---

## Part VI: Current Status

**Phase 0**: COMPLETE (Truth audit documented in Part I above)
**Phase 1**: IN PROGRESS (task list defined, implementation beginning)
**Phase 2-8**: PENDING

**Next Action**: Implement Phase 1 tasks, produce DOC-701 verification report.