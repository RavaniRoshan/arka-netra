<p align="center">
  <picture>
    <img alt="ArkaNetra" src="https://img.shields.io/badge/ArkaNetra-Physics--Informed%20Flare%20Warning-ff6f00?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAbwAAAG8B8aLcQwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAEPSURBVCiRjdKxSsNQGMbx33/OSZpY7NBF7CAI4uCkL6BTX8AX0MHFp3BxdnB28QVEcHZycBF0cBBcxEGweAFB1CY2yTn+DsbQVmNa5A/PH77h40iS9D+m3Yf++3n1Y2lAkkS1RqG+1Y8qT8Wl1XZ7PBoOh4O9nVY8sW2EECilYIxBEUGCZRkIAaUEYwxqOByhqj0iCRJQa4dI0mZJkq4R0W5ZlFmt2vC8HdI0mM0m7O3tI6UmDAMQQggBm4sQQJZldF1HURQMQ4P3u0f0Xc9aHMeO6Wq1mS0gFkU8PjwQxxH1eJ3Qa4EoQkqJdR3G2BiGYW0AURRhbYsQgvF4xP39HQBR6zLq9Xq02+35b3dKKaqqQimFcw4AtH7k/5IkSZKkf/ANm1dC5wH4V5QAAAAASUVORK5CYII=">
  </picture>
</p>

<h1 align="center">ArkaNetra</h1>
<p align="center">
  <strong>Physics-informed multimodal solar flare early-warning system</strong><br>
  Built for Aditya-L1 dual-band X-ray science · ISRO Problem Statement #15
</p>

<p align="center">
  <a href="https://github.com/your-org/arka-netra/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="#quick-start"><img alt="Quick Start" src="https://img.shields.io/badge/quick--start-3_steps-brightgreen"></a>
  <a href="https://www.isro.gov.in"><img alt="ISRO" src="https://img.shields.io/badge/mission-Aditya--L1-orange"></a>
  <a href="https://github.com/your-org/arka-netra/actions"><img alt="Build" src="https://img.shields.io/badge/build-passing-brightgreen"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#documentation">Docs</a> ·
  <a href="#contributing">Contributing</a>
</p>

---

> [!NOTE]
> **Hackathon-ready.** ArkaNetra is a working MVP with a Streamlit mission dashboard, a FastAPI prediction API, and 7 completed implementation phases — all backed by 79 passing tests.

---

## Why ArkaNetra

Solar flares threaten satellites, astronauts, communication networks, and power grids. Most flare prediction systems are black-box classifiers that output a probability and stop. ArkaNetra is different: it fuses **soft and hard X-ray data** — the two bands Aditya-L1 observes from the Sun-Earth L1 point — through a physics-informed multimodal architecture that explains *why* it raised a warning, not just *that* it did.

Five questions ArkaNetra answers for mission operators:

1. **Will a flare occur?** — short-range probability with class-specific risk
2. **How confident are we?** — Monte Carlo uncertainty band
3. **Why does the system believe this?** — top feature drivers + cross-modal attention
4. **Is the Sun behaving unusually?** — independent anomaly index
5. **What's the downstream risk?** — SEP radiation dose + satellite orbit risk

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-org/arka-netra.git
cd arka-netra
pip install -e .

# 2. Build MVP artifacts
python scripts/build_mvp.py

# 3. Launch the dashboard
streamlit run app/streamlit_app.py
```

Open **http://localhost:8501** and select a replay scenario. That's it.

---

## Features

| Category | Capability | Status |
|---|---|---|
| **Multimodal Fusion** | Dual-Branch Cross-Attention GRU fusing soft + hard X-ray time series | ✅ |
| **Physics-Informed** | Neupert-effect consistency, hardness ratio, integrated hard X-ray energy | ✅ |
| **Uncertainty** | Monte Carlo dropout confidence bands on every prediction | ✅ |
| **Anomaly Detection** | Independent quiet-Sun reconstruction error index (0–100) | ✅ |
| **Real Data** | GOES XRS soft X-ray download pipeline + cross-calibration for Aditya-L1 instruments | ✅ |
| **Evaluation** | Brier score, ECE, false alarm rate, lead-time analysis, SHAP explanations | ✅ |
| **Monitoring** | Drift detection, continuous validation, retrain triggers, pipeline orchestrator | ✅ |
| **Radiation Risk** | SEP model, human spaceflight dose estimation, satellite risk (LEO/MEO/GEO/HEO) | ✅ |
| **Operational API** | FastAPI with auth, rate limiting, and structured prediction/alerts/manifest endpoints | ✅ |
| **Docker** | Single `docker-compose up` for API + dashboard deployment | ✅ |
| **Streamlit Dashboard** | Replay scenarios, live gauges, attention heatmaps, feature drivers, alert history | ✅ |

---

## Architecture

```
                  ┌──────────────────┐
                  │   Aditya-L1 @ L1 │
                  │  SoLEXS │ HEL1OS │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  Data Pipeline   │
                  │  GOES / RHESSI / │
                  │  Fermi GBM proxy │
                  └────────┬─────────┘
                           │
          ┌────────────────▼────────────────┐
          │   Feature Engineering           │
          │   Soft X-ray · Hard X-ray       │
          │   Hardness ratio · Derivatives  │
          │   Integrated energy · Neupert   │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │  Dual-Branch Cross-Attn GRU     │
          │  ┌──────────┐  ┌──────────┐     │
          │  │ Soft GRU  │  │ Hard GRU  │     │
          │  └─────┬─────┘  └─────┬─────┘     │
          │        └─── cross ───┘           │
          └────────────────┬────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
  ┌──▼───┐          ┌──────▼──────┐       ┌──────▼──────┐
  │ Risk  │          │  Anomaly    │       │  Radiation  │
  │ Score │          │  Index      │       │  Risk       │
  └──┬───┘          └──────┬──────┘       └──────┬──────┘
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │  Mission Console │
                  │  (Streamlit)     │
                  └──────────────────┘
```

---

## Project Structure

```
arka-netra/
├── src/arkanetra/           # Core library
│   ├── api/                 # FastAPI prediction API
│   ├── data/                # Data pipeline: GOES, SoLEXS, HEL1OS, synthetic
│   ├── monitoring/          # Drift detection, validation, retrain orchestrator
│   ├── radiation/           # SEP model, human spaceflight dose, satellite risk
│   ├── alerts/              # Alert schema, lifecycle, audit logging
│   ├── archive/             # Forecast archive for operational continuity
│   ├── registry/            # Model registry with versioning
│   ├── models.py            # Scikit-learn baselines
│   ├── torch_models.py      # PyTorch Dual-Branch Cross-Attention GRU
│   ├── features.py          # Physics-inspired feature engineering
│   ├── evaluation.py        # Scientific evaluation suite
│   ├── anomaly.py           # Monte Carlo anomaly detection
│   ├── pipeline.py          # End-to-end MVP pipeline orchestration
│   └── config.py            # Centralized configuration
├── scripts/
│   ├── build_mvp.py         # Build all MVP artifacts
│   └── verify_mvp.py        # MVP integrity verification
├── app/
│   └── streamlit_app.py     # Streamlit mission console
├── tests/                   # 48 test modules, 79+ tests
├── docs/                    # 32 design & decision documents
├── models/registry/         # Serialized model checkpoints
├── data/                    # Raw & processed data
├── reports/                 # Generated predictions, metrics, manifests
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

---

## Commands

| Command | What it does |
|---|---|
| `make test` | Run all tests (79+ tests, 48 modules) |
| `make lint` | Lint with ruff |
| `make typecheck` | Type check with mypy |
| `make build` | Build Docker image |
| `make docker-run` | Start API + dashboard via docker-compose |
| `make docker-down` | Stop containers |
| `make dev-setup` | Full development environment in one command |

---

## Documentation

ArkaNetra ships with a 32-document knowledge base rooted in the Constitution (DOC-001):

- **[DOC-001](docs/DOC-001_ArkaNetra_Constitution_v1.0.md)** — Master Constitution: mission, science, architecture, philosophy
- **[DOC-700](docs/DOC-700_Grand_Unified_Implementation_Plan.md)** — Grand Unified Implementation Plan (all 7 phases)
- **[DOC-503](docs/DOC-503_Demo_Script.md)** — Judge-facing demo script

Browse the full documentation map: [`docs/`](docs/)

---

## Current Limitations

> [!WARNING]
> The current MVP uses deterministic **synthetic proxy data** so the full pipeline runs immediately. It is **not an operational forecast**. The next milestone replaces synthetic windows with curated GOES XRS + RHESSI/Fermi data and adds full PyTorch GRU training on real observations.

---

## Roadmap

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Real GOES XRS soft X-ray integration | ✅ |
| **Phase 2** | PyTorch Deep Learning activation (GRU) | ✅ |
| **Phase 3** | Comprehensive scientific evaluation | ✅ |
| **Phase 4** | Monitoring & continuous retraining | ✅ |
| **Phase 5** | SEP & radiation risk extension | ✅ |
| **Phase 6** | Operational platform hardening (API, Docker, CI/CD) | ✅ |
| **Phase 7** | Aditya-L1 mission integration (SoLEXS/HEL1OS) | ✅ |
| **Next** | Real-data training on GOES + RHESSI/Fermi | 🚧 |

---

## Contributing

ArkaNetra is built for **Bharatiya Antariksh Hackathon 2026** and welcomes contributions that strengthen its physics-informed thesis.

1. Fork the repo
2. Create a branch: `feature/your-feature` or `fix/your-fix`
3. Write tests alongside your changes
4. Ensure `make test && make lint && make typecheck` all pass
5. Open a PR with a clear description

See [`docs/DOC-001`](docs/DOC-001_ArkaNetra_Constitution_v1.0.md) for the project's architectural philosophy and design principles.

---

## License

[MIT](LICENSE) © 2026 ArkaNetra Contributors

---

<p align="center">
  <sub>Built with ☀️ for ISRO · Problem Statement #15 · Bharatiya Antariksh Hackathon 2026</sub>
</p>