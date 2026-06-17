# DOC-612: Publication and Collaboration Materials

**Project:** Project Solaris
**Version:** Phase 5 Final
**Date:** 2026-06-16
**Status:** COMPLETE

---

## Table of Contents

1. [Technical Report](#1-technical-report)
2. [Model Cards](#2-model-cards)
3. [Dataset Description](#3-dataset-description)
4. [API Reference](#4-api-reference)
5. [Contributing Guide](#5-contributing-guide)
6. [Pilot Collaboration Materials](#6-pilot-collaboration-materials)

---

## 1. Technical Report

### 1.1 Executive Summary

Project Solaris is a physics-informed multimodal solar flare early warning system designed for operational and research use. The system ingests near-real-time solar X-ray flux from multiple spacecraft (GOES, RHESSI, Fermi GBM, Aditya-L1 SoLEXS/HEL1OS) and produces probabilistic flare predictions with uncertainty quantification, anomaly detection, and radiation-risk context.

The Phase 5 upgrade introduces:
- A dual-branch GRU model with cross-attention (replacing the sklearn surrogate)
- A GRU autoencoder for physics-grounded anomaly detection
- An experimental SEP-risk module
- A model registry with versioned checkpointing
- A forecast archive with drift detection and automatic retraining triggers

### 1.2 System Architecture

```
Soft X-ray (GOES/SoLEXS) ──┐
                            ├─► Soft GRU Encoder ──┐
Hard X-ray (RHESSI/HEL1OS) ─┘                        ├─► Cross-Attention ──► Forecast Head ──► flare_probability
                            └─► Hard GRU Encoder ──┘

FEATURE_COLUMNS ──► GRU Autoencoder ──► anomaly_index (reconstruction error)

Physics Loss: d(SXR)/dt ≈ HXR (Neupert's Law) incorporated as supervised regularization term.
```

### 1.3 Data Flow

1. **Ingestion**: Fetch raw flux data from instrument adapters (SWPC, bundled samples)
2. **Quality control**: Apply quality flags, resample to uniform cadence
3. **Feature engineering**: Rolling statistics, hardness ratio, integrated hard X-ray energy
4. **Labeling**: Binary flare labels (M-class or above) within 120-minute horizon
5. **Splitting**: Chronological train/validation/test split
6. **Training**: GRU model with BCE + Neupert loss; autoencoder on quiet-Sun windows
7. **Inference**: Sequence windowing → GRU forward pass → sigmoid → Monte Carlo samples
8. **Post-processing**: Uncertainty, anomaly index, alert state, SEP risk
9. **Output**: Parquet/JSONL predictions, metrics CSV, audit log, manifest

### 1.4 Model Specifications

#### DualBranchCrossAttentionGRU

| Parameter | Default |
|-----------|---------|
| Soft dim | 5 (soft_xray_flux, soft_xray_derivative, rolling_mean, rolling_slope, rolling_volatility) |
| Hard dim | 4 (hard_xray_flux, hardness_ratio, integrated_hard_xray_energy, hard_rolling_slope) |
| Hidden dim | 64 |
| Num GRU layers | 2 |
| Dropout | 0.25 |
| Attention heads | 4 |
| Optimizer | Adam (lr=1e-3) |
| Loss | BCE + 0.18 × Neupert MSE |

#### GRUAutoencoder

| Parameter | Default |
|-----------|---------|
| Input dim | 12 (FEATURE_COLUMNS) |
| Hidden dim | 32 |
| Num GRU layers | 2 |
| Dropout | 0.25 |
| Lookback steps | 24 |
| Training data | Quiet-Sun windows (flare_label == 0) from train split |

### 1.5 Performance

Current baseline (sklearn surrogate on synthetic data):

| Model | Precision | Recall | F1 | PR-AUC | ROC-AUC |
|-------|-----------|--------|----|--------|---------|
| Random Forest Baseline | varies | varies | varies | varies | varies |
| Soft-Only Logistic | varies | varies | varies | varies | varies |
| Dual-Branch Surrogate (sklearn) | varies | varies | 0.893 | varies | varies |

GRU model performance depends on training data volume and hyperparameters; expected to match or exceed surrogate on sufficiently large multimodal datasets.

### 1.6 Limitations and Known Issues

1. **SEP risk is experimental**: The SEP risk index is derived from a heuristic model trained on limited data. It should not be used as a primary operational decision driver without validation against ground-truth SEP events.

2. **Satellite risk estimates are placeholders**: Radiation dose rates use simplified scaling factors. They do not account for spacecraft shielding, orbit specifics, or directional flux anisotropies.

3. **Limited training dataset**: Current MVP uses synthetic and bundled sample data. Model performance on live data has not been validated.

4. **Single-step forecasting**: The system produces a single forecast per timestep. Multi-horizon ensemble forecasting is planned for future versions.

5. **GRU requires PyTorch**: The GRU architecture adds a ~500MB dependency. The sklearn fallback requires no additional dependencies.

### 1.7 Citation

If you use Project Solaris in academic work, please cite:

```
Solaris: A Physics-Informed Multimodal Solar Flare Early Warning System.
Version 0.1 (Phase 5). 2026. https://github.com/anomalyco/solaris
```

---

## 2. Model Cards

### 2.1 SolarisFusionModel (sklearn surrogate)

**Model type:** StandardScaler + LogisticRegression with physics-informed feature augmentation  
**Task:** Binary flare prediction (M-class or above within 120 minutes)  
**Training data:** Synthetic/replay data from bundled samples or GOES  
**Features:** FEATURE_COLUMNS (12 features) + augmented cross-attention and Neupert consistency scores  
**Metrics:** F1=0.893 (MVP synthetic)  
**Known limitations:** Sklearn surrogate approximates GRU attention; no sequence modeling  
**Intended use:** Research, demo, baseline comparison  
**Out-of-scope:** Operational forecasting without validation on live data

### 2.2 DualBranchCrossAttentionGRU

**Model type:** PyTorch dual-branch GRU with multi-head cross-attention  
**Task:** Binary flare prediction  
**Training data:** Same as sklearn; requires lookback window of 24 timesteps  
**Features:** Soft X-ray sequence (5 features) + hard X-ray sequence (4 features)  
**Loss:** Binary cross-entropy + 0.18 × Neupert physics loss  
**Metrics:** Pending GRU training  
**Known limitations:** Requires PyTorch; training slow without GPU  
**Intended use:** Production upgrade, research collaboration  
**Out-of-scope:** Deployment without operational validation

### 2.3 GRUAutoencoder

**Model type:** PyTorch GRU encoder-decoder  
**Task:** Anomaly detection (reconstruction error on FEATURE_COLUMNS)  
**Training data:** Quiet-Sun windows (flare_label == 0) from train split  
**Features:** FEATURE_COLUMNS (12 features × lookback window)  
**Metrics:** Reconstruction error normalized to 0–100  
**Known limitations:** Requires retraining when feature set changes  
**Intended use:** Detecting novel flare precursor patterns  
**Out-of-scope:** Trojan/flare classification without downstream model

---

## 3. Dataset Description

### 3.1 Synthetic Data

The synthetic dataset (`solaris/data/synthetic.py`) generates realistic flare-like events under a Poisson process with a power-law burst duration distribution. It preserves the statistical properties of GOES observations without requiring external data access.

**Properties:**
- Cadence: 5 minutes (configurable)
- Columns: All FEATURE_COLUMNS + labels + upcoming event metadata
- Splits: Chronological: 60% train / 20% validation / 20% test
- Size: 1728 timesteps for default `periods: 1728` config

### 3.2 Sample GOES Data

`data/goes_sample.csv` contains a subset of real GOES observations bundled with the repository for fallback when SWPC API is unavailable.

### 3.3 Aditya-L1 Sample Data

- `data/solexs/solexs_sample.csv` — SoLEXS soft X-ray
- `data/hel1os/hel1os_sample.csv` — HEL1OS hard X-ray

### 3.4 Data Schema

All prediction outputs follow this schema:

```python
{
    "timestamp": datetime,
    "soft_xray_flux": float,
    "hard_xray_flux": float,
    "hardness_ratio": float,
    "soft_xray_derivative": float,
    "integrated_hard_xray_energy": float,
    "flare_label": int,               # Binary ground truth
    "upcoming_event_id": str | None,
    "upcoming_flare_class": str | None,
    "time_to_flare_minutes": float | None,
    "split": str,                     # train/validation/test
    "flare_probability": float,       # Mean of MC samples
    "uncertainty_variance": float,
    "confidence_low": float,          # 10th percentile
    "confidence_high": float,         # 90th percentile
    "anomaly_index": float,           # 0-100
    "mission_state": str,             # NORMAL/WATCH/WARNING/CRITICAL/UNCERTAIN
    "sep_risk_index": float,          # 0-100 (if radiation.sep_enabled)
    "sep_category": str,              # MINIMAL/LOW/MODERATE/HIGH
    "confidence": str,                # high/moderate/low
    "data_mode": str,                 # synthetic/goes_proxy/aditya_l1
    "model_version": str,
}
```

---

## 4. API Reference

### 4.1 Pipeline API

```python
from solaris.pipeline import build_dataset, make_predictions, write_reports, build_artifact_manifest
from solaris.config import load_config
from pathlib import Path

config = load_config("configs/mvp.yaml")
dataset, events = build_dataset(config)
predictions, bundle = make_predictions(dataset, config, events)
write_reports(Path("."), dataset, events, predictions, bundle, config)
manifest = build_artifact_manifest(Path("."), dataset, events, predictions, bundle.metrics, config=config)
```

### 4.2 Training API

```python
from solaris.models import ModelBundle, train_models, monte_carlo_uncertainty

bundle = train_models(dataset, config)
mean, variance, low, high = monte_carlo_uncertainty(
    probabilities, passes=40, seed=42
)
```

### 4.3 PyTorch Training API

```python
from solaris.training import train_gru_model, SequenceDataset

result = train_gru_model(
    train_frame=train_df,
    valid_frame=valid_df,
    config=config,
    output_dir=Path("models/registry/v1.0.0"),
)
# result = {"best_val_loss": ..., "best_val_f1": ..., "history": {...}, "model_state": {...}}
```

### 4.4 Radiation API

```python
from solaris.radiation import SEPRiskModel, SEPRiskResult, ParticleData, SatelliteRiskContext, assess_satellite_risk

sep_model = SEPRiskModel(particle_data=particle_data)
result: SEPRiskResult = sep_model.assess(
    upcoming_flare_class="M",
    hard_xray_behavior={"peak_flux": 50.0, "rise_rate": 3.0},
    uncertainty_variance=0.1,
    flare_probability=0.6,
)
print(result.sep_risk_index, result.sep_category)

sat_ctx = assess_satellite_risk(sep_risk_index=50, orbit=SatelliteOrbit.GEO)
```

### 4.5 Registry API

```python
from solaris.registry import ModelRegistry, get_registry

registry = get_registry(Path("models/registry"))
registry.register("v1.0.0", metrics=metrics_df, config_snapshot=config, architecture="gru")
entry = registry.get("v1.0.0")
registry.list_models()
registry.load_checkpoint_path("v1.0.0")
```

### 4.6 Archive API

```python
from solaris.archive import ForecastArchive, append_forecast

run_id = append_forecast(predictions, config=config, metrics=bundle.metrics)

archive = ForecastArchive(Path("archive"))
runs = archive.list_runs()
predictions_back = archive.load_predictions(run_id)
```

### 4.7 Monitoring API

```python
from solaris.monitoring import detect_drift, compute_drift_score, should_retrain

report = detect_drift(reference_df, current_df, threshold=0.15)
print(report.drift_detected, report.drifted_features)

retrain, reason = should_retrain(config, archive=archive)
```

### 4.8 Alerts API

```python
from solaris.alerts import AlertStateMachine, AlertRecord

sm = AlertStateMachine(config)
state = sm.compute_state(probability=0.72, anomaly_index=50, is_stale=False)

record = AlertRecord(
    timestamp=now,
    flare_probability=0.72,
    state="WARNING",
    threshold_used="critical",
)
sm.update(record)
```

### 4.9 FastAPI Endpoints

```bash
uvicorn solaris.api.prediction_api:app --host 0.0.0.0 --port 8080
```

| Endpoint | Method | Response |
|----------|--------|----------|
| `/health` | GET | `{"status": "ok"}` |
| `/predictions` | GET | JSON list of prediction dicts |
| `/alerts` | GET | `{"alerts": [...], "count": N}` |
| `/manifest` | GET | Artifact manifest JSON |
| `/audit` | GET | List of audit log entries |
| `/scenarios` | GET | Distinct scenario labels from predictions |

---

## 5. Contributing Guide

### 5.1 Development Setup

```bash
git clone <repository-url>
cd solaris
python -m venv .venv
.venv/scripts/activate  # Windows
pip install -e ".[dev]"
```

### 5.2 Running Tests

```bash
pytest tests/ -q --tb=short
```

### 5.3 Code Conventions

- **Type hints:** Use `from __future__ import annotations`
- **Imports:** stdlib → third-party → local
- **Style:** Follow existing code conventions; no comments unless requested
- **Tests:** Add tests for new features in `tests/test_<module>.py`
- **Documentation:** Add a corresponding DOC-XXX file for each major feature

### 5.4 Making Changes

1. Create a new branch from `main`
2. Implement changes with tests
3. Run `python scripts/verify_mvp.py`
4. Update `docs/DOC-402_Task_Board.md` and `docs/DOC-002_Decision_Log.md`
5. Submit PR with description of changes and verification results

### 5.5 Adding a New Data Source

1. Create `src/solaris/data/<source>.py`
2. Implement `build_<source>_replay(config)` returning `(DataFrame, events_df)`
3. Register in `pipeline.py::build_dataset`
4. Add tests in `tests/test_<source>_adapter.py`
5. Add DOC file describing the source interface

### 5.6 Adding a New Model Architecture

1. Add model class in `src/solaris/models.py` or `src/solaris/torch_models.py`
2. Update `train_models()` to support the new architecture
3. Add toggle to `configs/mvp.yaml::model.architecture`
4. Update `compute_anomaly_index` if anomaly detection changes
5. Add tests verifying the new architecture trains and predicts correctly

---

## 6. Pilot Collaboration Materials

### 6.1 Dataset Sharing

Project Solaris publishes the following datasets for collaboration:

| Dataset | Format | Access |
|---------|--------|--------|
| Synthetic training data | Parquet | Bundled with repo |
| GOES sample data | CSV | Bundled with repo |
| Aditya-L1 sample data | CSV | Bundled with repo |
| Prediction outputs | Parquet/JSONL | `reports/` directory |

### 6.2 Model Access

Trained models are stored in `models/registry/` with versioned checkpoints and config snapshots.

```python
from solaris.registry import get_registry
registry = get_registry()
latest = registry.get_latest()
```

### 6.3 Collaboration Workflows

**Research collaboration:**
1. Clone the repository and run `pip install -e .`
2. Run `python scripts/verify_mvp.py` to verify baseline
3. Apply changes with tests
4. Share run outputs via `archive/` or `reports/`

**Operational pilot:**
1. Configure `data.mode: goes_proxy` for live data
2. Set `model.architecture: gru` with trained checkpoint
3. Enable `radiation.sep_enabled: true` with particle data
4. Monitor via FastAPI dashboard
5. Review `reports/audit_log.jsonl` for compliance

### 6.4 Contact and Feedback

- **Document:** Changes tracked in `docs/DOC-402_Task_Board.md`
- **Decisions:** Logged in `docs/DOC-002_Decision_Log.md`
- **Issues:** Report via standard issue tracking
- **Releases:** Tagged with Phase completion status (Phase 1–5)

### 6.5 Pilot Checklist

Before beginning an operational pilot:

- [ ] All 79+ tests pass
- [ ] GRU model has been trained and evaluated
- [ ] Model card completed for deployed model version
- [ ] Alert thresholds validated against known events
- [ ] Audit log reviewed for compliance
- [ ] Data source (live or sample) quality verified
- [ ] Dashboard and API tested end-to-end
- [ ] Runbook completed (DOC-611 Section 8)
- [ ] Operational assumptions documented
- [ ] Exit plan defined

---

## Appendix A: Abbreviations

| Abbreviation | Meaning |
|--------------|---------|
| GRU | Gated Recurrent Unit |
| SEP | Solar Energetic Particle |
| GOES | Geostationary Operational Environmental Satellite |
| RHESSI | Reuven Ramaty High Energy Solar Spectroscopic Imager |
| GBM | Gamma-ray Burst Monitor (Fermi) |
| SoLEXS | Soft X-ray Spectrometer (Aditya-L1) |
| HEL1OS | High Energy L1 Orbiting X-ray Spectrometer (Aditya-L1) |
| F1 | F1 Score |
| PR-AUC | Precision-Recall Area Under Curve |
| ROC-AUC | Receiver Operating Characteristic AUC |
| PCA | Principal Component Analysis |
| BCE | Binary Cross-Entropy Loss |
| UTC | Coordinated Universal Time |

## Appendix B: Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-06-16 | Project Solaris | Phase 5 final — GRU architecture, radiation risk, model registry, archive, monitoring |

---

*End of DOC-612*