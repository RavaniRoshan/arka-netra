# DOC-008: ArkaNetra Constitution Coverage Audit

**Audit date:** 2026-06-17  
**Source of truth:** `docs/DOC-001_ArkaNetra_Constitution_v1.0.md`  
**Scope:** Code, generated artifacts, tests, dashboard, API, monitoring, radiation modules, and phase verification reports.

## Executive Summary

**Overall DOC-001 constitution compliance: 47%.**

ArkaNetra has a strong hackathon MVP: deterministic replay data, physics-inspired features, labels, sklearn surrogate model, uncertainty-like confidence bands, PCA anomaly index, alert state machine, API, monitoring reports, and a Streamlit replay dashboard. The system is runnable and passes verification:

- `python scripts/build_mvp.py` completed successfully.
- `python scripts/verify_mvp.py` passed with 1,728 rows and four replay scenarios.
- `python -m pytest tests/ -q` passed 257/257 tests.
- Streamlit launched successfully with HTTP 200.
- API validation bug fixed: invalid `/predictions?scenario=...` now returns 400 when predictions are unavailable.
- SWPC JSON parsing hardened to tolerate NUL bytes in live response payloads.

However, the MVP is not yet a 100% DOC-001-compliant system. The largest gaps are:

1. **The canonical model is not the active production path.** `DualBranchCrossAttentionGRU` exists and has a training path, but `train_models()` defaults to an sklearn surrogate at `src/arkanetra/models.py:223-265`.
2. **Aditya-L1 live ingestion is not operational.** SoLEXS/HEL1OS endpoints are present but currently fail DNS in this environment; sample data and graceful fallbacks exist.
3. **Uncertainty is approximated, not true Monte Carlo Dropout.** `monte_carlo_uncertainty()` perturbs probabilities at `src/arkanetra/models.py:277-285` instead of running an actual PyTorch model with dropout enabled.
4. **Anomaly detection is PCA by default.** GRU autoencoder anomaly detection is optional at `src/arkanetra/anomaly.py:111-134`, not the active default.
5. **Dashboard is conditional and incomplete after MVP build.** The code supports 5 tabs only if extra Phase 6 artifacts exist; the current build creates the core replay dashboard, not all five artifact-backed tabs.
6. **Phase verification reports overclaim operational completeness.** DOC-701 through DOC-707 claim phase completion, but several modules remain scaffolded, experimental, or proxy-only.

## Coverage by DOC-001 Area

| DOC-001 Area | Coverage | Status |
|---|---:|---|
| Mission framing and ISRO relevance | 90% | Implemented in docs and product copy |
| Domain understanding and problem framing | 85% | Strong narrative, limited real validation |
| Aditya-L1 data identity | 35% | Future identity present; live ingestion not validated |
| Data ingestion and harmonization | 45% | Synthetic, GOES, RHESSI/Fermi paths present; live data fragile |
| Mandatory feature engineering | 90% | All required features implemented |
| Forecast labels and windows | 85% | Implemented with event labels and forecast horizon |
| Dual-Branch Cross-Attention GRU | 35% | Defined and trainable, but not active default |
| Cross-attention fusion | 35% | PyTorch module exists; active model uses surrogate attention |
| Physics-informed Neupert learning | 55% | GRU loss exists; active surrogate uses diagnostic only |
| Uncertainty quantification | 40% | Confidence bands exist; true MC Dropout not implemented |
| Explainability | 65% | Feature importance, attention heatmap, SHAP fallback present |
| GRU autoencoder anomaly detection | 45% | GRU AE exists; PCA is active default |
| Evaluation and ablations | 80% | Metrics, lead time, FAR, calibration, ablation implemented |
| Dashboard replay/product workflow | 60% | Replay works; five-tab Phase 6 artifacts not fully generated |
| Alert lifecycle and auditability | 85% | State machine, alert history, audit log implemented |
| API and operational hardening | 70% | Auth, rate limiting, validation, health checks present |
| Monitoring and retraining | 65% | Drift, validation, status reports present; no scheduler/DB |
| SEP and radiation risk | 45% | Experimental modules present; not validated |
| Documentation hierarchy | 70% | Many docs exist; DOC-101/102/103/201/202/203/301/302/303/304 missing |
| Reproducibility and artifacts | 75% | Build, manifest, metrics, predictions, monitoring reports generated |

## Detailed Requirement Map

### Implemented

| Requirement | Evidence |
|---|---|
| Modular package structure | `src/arkanetra/`, `app/`, `configs/`, `docs/`, `reports/` |
| Synthetic proxy replay | `src/arkanetra/data/synthetic.py:7-79` |
| GOES proxy path | `src/arkanetra/data/goes.py:159-260` |
| Hard X-ray proxy path | `src/arkanetra/data/hard_xray_proxy.py:203-259` |
| Mandatory features | `src/arkanetra/features.py:19-77` |
| Forecast labeling | `src/arkanetra/data/windows.py:7-25` |
| Chronological and event-based splits | `src/arkanetra/data/splits.py:7-95` |
| Baseline models | `src/arkanetra/models.py:228-239` |
| Surrogate final model | `src/arkanetra/models.py:260-265` |
| Probability, confidence band, anomaly, mission state | `src/arkanetra/pipeline.py:58-98` |
| Alert state machine | `src/arkanetra/alerts/lifecycle.py:37-114` |
| API auth/rate limiting/validation | `src/arkanetra/api/prediction_api.py:87-120`, `src/arkanetra/api/prediction_api.py:180-208` |
| Monitoring drift/status reports | `src/arkanetra/monitoring/drift.py:38-117`, `src/arkanetra/monitoring/orchestrator.py:28-215` |
| Dashboard replay | `app/streamlit_app.py:73-204` |
| Metrics and evaluation artifacts | `src/arkanetra/evaluation.py:82-210` |

### Partial

| Requirement | Current State | Gap |
|---|---|---|
| Aditya-L1 as target mission data | SoLEXS/HEL1OS adapters exist at `src/arkanetra/data/solexs.py:107-157` and `src/arkanetra/data/hel1os.py:110-145` | Live URLs fail DNS; no validated SoLEXS/HEL1OS ingestion |
| Cross-calibration | Implemented experimentally at `src/arkanetra/data/cross_calibration.py:47-224` | No real overlapping SoLEXS/GOES or HEL1OS/RHESSI validation |
| PyTorch GRU model | Defined at `src/arkanetra/torch_models.py:27-56` | Not active default; active default is sklearn surrogate |
| Physics loss | `neupert_loss()` exists at `src/arkanetra/torch_models.py:104-116` | Only active if `architecture="gru"` and torch path is used |
| MC Dropout uncertainty | Confidence bands generated at `src/arkanetra/models.py:277-285` | Does not run actual dropout inference |
| GRU autoencoder anomaly | `GRUAutoencoder` exists at `src/arkanetra/torch_models.py:59-73`; optional path at `src/arkanetra/anomaly.py:34-108` | PCA is active default |
| Dashboard product modes | Replay mode works | Analysis, Model Comparison, Multi-Horizon, Event Summary Export are conditional on missing artifacts |
| SEP/radiation risk | SEP, satellite, and human-spaceflight modules exist | All are experimental and not validated for operational use |
| Monitoring/retraining | Drift, validation, reports exist | No scheduler, database, rollback, or operational retraining pipeline |

### Scaffolded or Missing

| Requirement | Status |
|---|---|
| Operational Aditya-L1 data feed | Missing |
| Validated SoLEXS/HEL1OS cross-calibration | Missing |
| True Dual-Branch Cross-Attention GRU as production model | Scaffolded |
| True Monte Carlo Dropout inference | Missing |
| Multi-head severity and time-to-flare forecasting | Partial; fields are estimated/labeled, not learned as dedicated heads |
| 3D time-energy spectrogram | Missing |
| Operational scheduler | Missing |
| Database-backed audit/archive | Missing |
| Role-based access control | Missing |
| Webhook/push alerting | Missing |
| DOC-101/102/103 and DOC-201/202/203 | Missing |
| DOC-301/302/303/304 system design documents | Missing |

## Verification Findings

### Passing

- Full test suite: **257/257 passed**.
- MVP build: completed.
- MVP verification: passed with 1,728 rows and four scenarios.
- Streamlit launch: HTTP 200.
- API tests: 24/24 passed.
- Download tests: 4/4 passed after JSON hardening.

### Fixed During Audit

1. **API invalid scenario validation bug**
   - File: `src/arkanetra/api/prediction_api.py:180-208`
   - Problem: validation happened after the empty-predictions return, so invalid scenario returned 200 when predictions were unavailable.
   - Fix: validate scenario before returning an empty response.

2. **SWPC JSON NUL-byte parsing issue**
   - Files: `src/arkanetra/data/download.py:16-31`, `src/arkanetra/data/goes.py:54-69`
   - Problem: live SWPC flare JSON response can include trailing NUL bytes, causing `json.JSONDecodeError`.
   - Fix: strip NUL bytes and surrounding whitespace before JSON parsing.

## Coverage Conclusion

ArkaNetra is a credible **hackathon MVP**, not yet a DOC-001-complete operational platform.

A defensible pitch should say:

> ArkaNetra has a working, tested, replayable MVP that implements the core decision-support workflow: dual-band X-ray replay, physics-informed features, risk probability, confidence band, anomaly index, alert state, explanation artifacts, monitoring reports, API access, and dashboard replay. The canonical architecture is present in code, but the final operational model, live Aditya-L1 ingestion, true MC Dropout, validated anomaly detection, and operational deployment controls still need to be completed.

## Path to 100% Constitution Compliance

1. Make `DualBranchCrossAttentionGRU` the active production model and keep sklearn as a baseline.
2. Implement true Monte Carlo Dropout inference with dropout enabled during repeated PyTorch passes.
3. Make GRU autoencoder anomaly detection the default or provide a clear config flag explaining why PCA is used.
4. Validate SoLEXS/HEL1OS data ingestion against real or archived Aditya-L1 datasets.
5. Add real cross-calibration reports using overlapping instrument windows.
6. Generate all five dashboard artifact sets so the dashboard consistently renders all five tabs.
7. Add operational deployment controls: scheduler, DB-backed audit/archive, rollback, role access, and webhook alerting.
8. Complete missing DOC-101/102/103 and DOC-201/202/203 and DOC-301/302/303/304 documents.
9. Replace phase reports' overclaim language with honest scaffolded/partial/validated status labels.
10. Add an end-to-end demo script using real or archived non-synthetic data, not only synthetic proxy replay.
