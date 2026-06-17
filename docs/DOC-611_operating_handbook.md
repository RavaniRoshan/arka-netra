# DOC-611: ArkaNetra Operating Handbook

**Project:** ArkaNetra
**Version:** mvp-0.1 / Phase 5
**Date:** 2026-06-16
**Status:** COMPLETE

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Quick Start](#2-quick-start)
3. [Configuration Guide](#3-configuration-guide)
4. [Architecture Reference](#4-architecture-reference)
5. [Running the System](#5-running-the-system)
6. [Interpreting Outputs](#6-interpreting-outputs)
7. [Radiation Risk Module](#7-radiation-risk-module-experimental)
8. [Monitoring and Maintenance](#8-monitoring-and-maintenance)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. System Overview

ArkaNetra is a physics-informed multimodal solar flare early warning system. It ingests soft X-ray (GOES/SoLEXS) and hard X-ray (RHESSI/Fermi/HEL1OS) data and produces probabilistic flare predictions with uncertainty quantification, anomaly detection, and radiation-risk context.

**Core capabilities:**
- Flare probability prediction (M/W/C/X-class) with 120-minute forecast horizon
- Monte Carlo uncertainty estimation (40-pass dropout approximation)
- Anomaly detection (PCA reconstruction error or GRU autoencoder)
- Alert lifecycle with configurable thresholds
- Audit provenance (config/data hash, append-only log)
- SEP-risk model (experimental, separate from flare prediction)
- Satellite radiation context (informational only)
- Model registry with versioned checkpoints
- Forecast archive with drift detection

**Three data modes:**
- `synthetic` — bundled sample data, no external dependencies
- `goes_proxy` — NOOA SWPC GOES data (primary) + bundled sample (fallback)
- `aditya_l1` — SoLEXS (soft X-ray) + HEL1OS (hard X-ray) sample data

**Two model architectures:**
- `sklearn` — LogisticRegression surrogate (default, no PyTorch required)
- `gru` — DualBranchCrossAttentionGRU with PyTorch (set `model.architecture: gru`)

---

## 2. Quick Start

### Run the full pipeline

```bash
python -m arkanetra.pipeline run --config configs/mvp.yaml --output run_output/
```

### Run the dashboard

```bash
streamlit run app/streamlit_app.py
```

### Run tests

```bash
pytest tests/ -q
```

### Run MVP verification

```bash
python scripts/verify_mvp.py
```

### Default output artifacts

| File | Description |
|------|-------------|
| `reports/metrics.csv` | Model evaluation metrics |
| `reports/event_summary.csv` | Per-scenario alert event summary |
| `reports/alert_history.csv` | Alert state history |
| `reports/audit_log.jsonl` | Append-only audit log |
| `reports/predictions/predictions.jsonl` | Per-timestep predictions |
| `reports/artifact_manifest.json` | Evidence manifest with staleness |

---

## 3. Configuration Guide

All configuration lives in `configs/mvp.yaml`. Below is the complete reference.

### 3.1 Project

```yaml
project:
  name: ArkaNetra
  version: mvp-0.1    # Shown in predictions output
  mode: replay        # replay | live (future)
```

### 3.2 Data

```yaml
data:
  mode: synthetic    # synthetic | goes_proxy | aditya_l1

  # goes_proxy mode options:
  goes_source: auto  # auto | swpc | sample
  goes_event_window_hours: 48

  # hard X-ray source:
  hard_source: auto   # auto | rhessi | fermi | sample

  # Common:
  start: "2026-01-01T00:00:00Z"
  periods: 1728       # Number of timesteps (5-min cadence = 6 days)
  cadence_minutes: 5
  forecast_horizon_minutes: 120  # Look-ahead for flare labels
  lookback_steps: 24            # GRU sequence length
  random_seed: 42

  # aditya_l1 mode options:
  aditya_l1:
    soft_source: solexs_sample   # solexs_sample | solexs_live (future)
    hard_source: hel1os_sample   # hel1os_sample | hel1os_live (future)
    hel1os_energy_band: "25-100 keV"
    payload_metadata: true
```

### 3.3 Features

```yaml
features:
  smoothing_window: 3    # Rolling mean window for smoothed flux
  rolling_window: 12     # Window for trend features
  hardness_epsilon: 1.0e-10  # Prevent division by zero
```

### 3.4 Model

```yaml
model:
  architecture: sklearn   # sklearn | gru

  random_seed: 42
  neupert_lambda: 0.18    # Physics-consistency weight in GRU training
  mc_dropout_passes: 40   # MC dropout passes for uncertainty
  warning_threshold: 0.55 # Flare probability threshold for WARNING state

  # GRU architecture options (used when architecture: gru)
  gru:
    hidden_dim: 64
    num_layers: 2
    dropout: 0.25
    lookback_steps: 24
    batch_size: 64
    learning_rate: 0.001
    epochs: 50
    ae_hidden_dim: 32     # Autoencoder hidden dim for anomaly detection
```

**To use PyTorch GRU:**
```yaml
model:
  architecture: gru
```

**To use sklearn (default):**
```yaml
model:
  architecture: sklearn
```

### 3.5 Alert Policy

```yaml
alert_policy:
  watch_probability: 0.35
  warning_probability: 0.55
  critical_probability: 0.78
  anomaly_watch: 45       # Anomaly index threshold for WATCH
  anomaly_supporting_warning: 70  # Anomaly index supporting WARNING
```

### 3.6 Radiation (Experimental)

```yaml
radiation:
  sep_enabled: false      # Enable SEP risk model
  particle_source: none  # none | goes_eps | goes_sees
  satellite_risk_enabled: false
  satellite_orbit: geostationary  # geostationary | l1 | leo | meo
```

### 3.7 Model Registry

```yaml
registry:
  enabled: false
  path: models/registry
```

### 3.8 Archive

```yaml
archive:
  enabled: false
  path: archive
  max_runs: 100
```

### 3.9 Monitoring

```yaml
monitoring:
  drift_threshold: 0.15        # Feature drift threshold
  consecutive_drift_count: 3   # Consecutive drifts to trigger retrain
  max_age_hours: 168.0         # Max model age before retrain
  min_runs_before_retrain: 5
  retrain_trigger: manual       # manual | auto
```

---

## 4. Architecture Reference

### 4.1 sklearn Architecture (Default)

The default `ArkaNetraFusionModel` uses:
- Feature augmentation: cross-attention score, Neupert consistency, physics-weighted risk
- StandardScaler + LogisticRegression (class_weight=balanced)
- Monte Carlo uncertainty via logit perturbation

### 4.2 GRU Architecture (PyTorch)

When `model.architecture: gru`:
- **DualBranchCrossAttentionGRU**: Two separate GRU encoders for soft and hard X-ray sequences, merged via multi-head cross-attention, with forecast head
- **GRUAutoencoder**: Trained on quiet-Sun (non-flare) windows; reconstruction error used as anomaly score
- **Training**: BCE loss + Neupert physics loss (weighted by `neupert_lambda`)
- **Checkpointing**: Saved to `models/registry/<version>/model_checkpoint.pt`

### 4.3 Anomaly Detection

| Config | Method |
|--------|--------|
| `architecture: sklearn` | PCA reconstruction error on FEATURE_COLUMNS |
| `architecture: gru` | GRU autoencoder reconstruction error |

Both produce a 0–100 anomaly index.

---

## 5. Running the System

### 5.1 Full Pipeline

```python
from arkanetra.config import load_config
from arkanetra.pipeline import build_dataset, make_predictions, write_reports

config = load_config("configs/mvp.yaml")
dataset, events = build_dataset(config)
predictions, bundle = make_predictions(dataset, config, events)
write_reports(Path("output"), dataset, events, predictions, bundle, config)
```

### 5.2 FastAPI Server

```bash
uvicorn arkanetra.api.prediction_api:app --reload
```

Endpoints:
- `GET /health` — Service health check
- `GET /predictions` — Current predictions
- `GET /alerts` — Active alert state
- `GET /manifest` — Artifact manifest
- `GET /audit` — Audit log entries
- `GET /scenarios` — Scenario list

### 5.3 Dashboard

```bash
streamlit run app/streamlit_app.py
```

Panels: Scenario selector, Metrics table, Event summary, Attention heatmap, Alert history, Audit log, Evidence panel, Staleness indicator.

---

## 6. Interpreting Outputs

### 6.1 Flare Probability

`flare_probability` is the mean of 40 Monte Carlo samples. It represents the probability of a M-class or larger flare within the forecast window (default: 120 minutes).

**Interpretation:**
| Range | State | Action |
|-------|-------|--------|
| < 0.35 | NORMAL | Background monitoring |
| 0.35–0.55 | WATCH | Analyst review recommended |
| 0.55–0.78 | WARNING | Action recommended |
| ≥ 0.78 or (p≥0.65 + anomaly≥70) | CRITICAL | Immediate action |

### 6.2 Uncertainty

`uncertainty_variance` is the variance of 40 MC samples. High variance (>0.15) indicates the model is uncertain and the probability estimate should be treated with caution.

`confidence_low` and `confidence_high` are the 10th and 90th percentiles.

### 6.3 Anomaly Index

`anomaly_index` (0–100) measures how unusual the current feature pattern is compared to quiet-Sun training data.

| Range | Meaning |
|-------|---------|
| < 45 | Normal quiet-Sun behavior |
| 45–70 | Elevated; WATCH supporting |
| ≥ 70 | WARNING supporting |

### 6.4 Alert States

NORMAL → WATCH → WARNING → CRITICAL → RESOLVED (or UNCERTAIN if data is stale)

---

## 7. Radiation Risk Module (Experimental)

**Important:** All radiation risk outputs are experimental and informational only.

### 7.1 SEP Risk Index

When `radiation.sep_enabled: true`, predictions include:

| Column | Description |
|--------|-------------|
| `sep_risk_index` | 0–100 SEP risk score |
| `sep_category` | MINIMAL / LOW / MODERATE / HIGH |
| `confidence` | high / moderate / low |
| `contributing_factors` | List of contributing factors |
| `is_experimental` | Always `true` |
| `particle_data_available` | Whether particle data was used |

SEP risk is **separate** from flare probability. A high `flare_probability` with low `sep_risk_index` is possible (e.g., low-latitude flare with poor magnetic connectivity).

### 7.2 Satellite Risk Context

When `radiation.satellite_risk_enabled: true`:

| Column | Description |
|--------|-------------|
| `sat_risk_level` | MINIMAL / LOW / MODERATE / HIGH |
| `sat_cumulative_dose_rate` | Estimated dose rate (arbitrary units) |
| `sat_radiation_context` | Plain-language context |
| `sat_advisory` | Operational advisory |
| `disclaimer` | Always: "Satellite radiation context is informational only" |

**Satellite orbits:** geostationary (GEO), L1, LEO, MEO

### 7.3 Particle Data Sources

| Source | Description |
|--------|-------------|
| `none` | No particle data; SEP risk based on flare class and X-ray behavior |
| `goes_eps` | GOES Energetic Particle Sensor (when available via SWPC) |

---

## 8. Monitoring and Maintenance

### 8.1 Model Registry

```python
from arkanetra.registry import get_registry

registry = get_registry(Path("models/registry"))
registry.register(
    model_version="v1.0.0",
    metrics=metrics_df,
    config_snapshot=config,
    architecture="sklearn",
)
registry.list_models()
registry.get("v1.0.0")
registry.load_checkpoint_path("v1.0.0")
```

### 8.2 Forecast Archive

```python
from arkanetra.archive import append_forecast

run_id = append_forecast(predictions, config=config, metrics=bundle.metrics)
```

```python
from arkanetra.archive import ForecastArchive

archive = ForecastArchive(Path("archive"))
runs = archive.list_runs()
archive.load_predictions(run_id)
```

### 8.3 Drift Detection

```python
from arkanetra.monitoring import detect_drift

report = detect_drift(reference_data, current_data, threshold=0.15)
print(report.drift_detected, report.drift_score, report.drifted_features)
```

### 8.4 Retraining Triggers

```python
from arkanetra.monitoring import should_retrain

should_retrain, reason = should_retrain(config, archive=archive)
```

Triggers fire when:
- Consecutive drift detections ≥ `consecutive_drift_count`
- Model age > `max_age_hours`

### 8.5 Retraining Checklist

1. Identify retrain trigger in `monitoring.log`
2. Verify new data quality (check `quality_flag` in data source)
3. Run pipeline with new data: `python -m arkanetra.pipeline run --config configs/mvp.yaml`
4. Compare new metrics against baseline in `reports/metrics.csv`
5. If acceptable, register new model version:
   ```python
   registry.register("v1.1.0", metrics=new_metrics, config_snapshot=config)
   ```
6. Archive old model: copy `models/registry/<old_version>/` to `models/registry/archive/`

---

## 9. Troubleshooting

### Problem: Tests fail after upgrade

```bash
# Verify all tests pass
python -m pytest tests/ -q

# Run MVP verification
python scripts/verify_mvp.py
```

### Problem: Dashboard shows stale data

1. Check `reports/artifact_manifest.json` → `staleness` field
2. If `is_stale: true`, run the pipeline again with fresh data
3. Check `reports/audit_log.jsonl` for data quality issues

### Problem: GRUTorch not available

When `model.architecture: gru` but PyTorch is not installed:
- Error: `RuntimeError: PyTorch is not installed. Install torch to use GRU models.`
- Fix: `pip install torch`
- Alternative: Set `model.architecture: sklearn` to use sklearn fallback

### Problem: GOES data fetch fails (404)

Expected behavior. The system falls back to bundled sample data automatically.
Check `data/goes_sample.csv` exists.

### Problem: Alert state not updating

Check `alert_history.csv` for recent entries.
Verify `alert_policy` thresholds in config.
Check `AlertStateMachine.compute_state()` handles the probability correctly.

### Problem: Drift detection fires incorrectly

Reduce `drift_threshold` in config (e.g., 0.15 → 0.25 for less sensitivity).
Check that reference and current data cover similar time periods.

---

## Appendix A: File Structure

```
src/arkanetra/
├── __init__.py
├── pipeline.py          # build_dataset, make_predictions, write_reports
├── config.py            # load_config, ensure_directories
├── features.py          # add_features, FEATURE_COLUMNS
├── models.py            # train_models, ArkaNetraFusionModel, GRUModel
├── anomaly.py           # compute_anomaly_index (PCA or GRU AE)
├── torch_models.py      # DualBranchCrossAttentionGRU, GRUAutoencoder
├── training.py          # SequenceDataset, train_gru_model
├── data/
│   ├── goes.py          # GOES adapter
│   ├── hard_xray_proxy.py  # RHESSI/Fermi adapter
│   ├── solexs.py        # SoLEXS adapter (Aditya-L1)
│   ├── hel1os.py        # HEL1OS adapter (Aditya-L1)
│   ├── synthetic.py     # Synthetic data generator
│   ├── staleness.py     # compute_staleness_score, detect_data_gaps
│   └── ...
├── alerts/
│   ├── schema.py        # AlertRecord
│   ├── lifecycle.py     # AlertStateMachine
│   └── audit.py         # write_audit_log, config_hash, data_hash
├── radiation/           # Phase 5: SEP and satellite risk
│   ├── sep_model.py
│   ├── particle_data.py
│   └── satellite_risk.py
├── registry/            # Phase 5: Model versioning
│   └── model_registry.py
├── archive/             # Phase 5: Forecast history
│   └── forecast_archive.py
├── monitoring/          # Phase 5: Drift and retrain
│   ├── drift.py
│   └── retrain.py
└── api/
    └── prediction_api.py  # FastAPI app
```

## Appendix B: Feature Columns

```
FEATURE_COLUMNS = [
    "soft_xray_flux",
    "hard_xray_flux",
    "hardness_ratio",
    "soft_xray_derivative",
    "integrated_hard_xray_energy",
    "waiting_time_since_previous_flare",
    "rolling_mean",
    "rolling_variance",
    "rolling_slope",
    "rolling_volatility",
    "hard_rolling_mean",
    "hard_rolling_slope",
]
```

## Appendix C: Alert State Transitions

```
NORMAL ──(p≥watch or a≥anomaly_watch)──→ WATCH
  ↑                                      │
  │                              (p≥warning or p≥(warning+0.10) and a≥anomaly_supporting_warning)
  │                                      ↓
RESOLVED ←──(p<watch and a<anomaly_watch)── WARNING
  │                                      │
  │                              (p≥critical or p≥(warning+0.10) and a≥anomaly_supporting_warning)
  │                                      ↓
  └─────────────────────────── CRITICAL
                               UNCERTAIN ←── (data is stale)
```

---

*Document version: 1.0 | Last updated: 2026-06-16*