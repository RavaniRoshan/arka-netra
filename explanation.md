# ArkaNetra MVP Explanation

Visual explanation of what has been built so far, how the current MVP works, and how the workflow moves from the current demo-hardened state toward the final full version.

Source of truth: `docs/DOC-001_Project_ArkaNetra_Constitution_v1.0.md`  
Current implementation baseline: Milestone 1.1 demo-hardened MVP  
Current data mode: synthetic proxy replay  
Current product mode: replay-first mission console  

## 1. What We Have Built So Far

ArkaNetra is currently a runnable MVP for a physics-informed, multimodal solar flare early-warning workflow. It is not yet an operational solar forecasting system. It is a working product skeleton that proves the end-to-end contract:

- Generate or ingest soft and hard X-ray-like time series.
- Compute physics-inspired features.
- Label short-horizon flare risk.
- Train baseline and multimodal-surrogate models.
- Produce flare probability, uncertainty, anomaly index, alert state, explanations, and replay scenarios.
- Serve those outputs through a Streamlit mission-console dashboard.
- Save evidence artifacts for judging and verification.

```mermaid
flowchart TD
    A["DOC-001 Constitution"] --> B["Architecture Thesis"]
    B --> C["MVP Pipeline"]
    C --> D["Synthetic Proxy Replay Data"]
    C --> E["Physics-Inspired Features"]
    C --> F["Model + Uncertainty + Anomaly"]
    F --> G["Prediction Artifacts"]
    G --> H["Streamlit Mission Console"]
    G --> I["Reports + Manifest + Verification"]
    I --> J["Milestone 1.1 Demo-Hardened MVP"]
```

## 2. Current MVP Product View

The current MVP is designed to look and behave like a mission-control replay console. A judge or team member can select a replay scenario and inspect risk, uncertainty, anomaly behavior, feature drivers, attention snapshot, and model comparison.

```mermaid
flowchart LR
    User["User / Judge"] --> Console["ArkaNetra Mission Console"]
    Console --> Scenario["Replay Scenario Selector"]
    Scenario --> Quiet["Quiet Sun replay"]
    Scenario --> CClass["C-class watch replay"]
    Scenario --> MClass["M-class warning replay"]
    Scenario --> XClass["X-class critical replay"]
    Scenario --> Archive["Background archive"]
    Console --> Risk["Flare Risk Gauge"]
    Console --> Uncertainty["Confidence Band"]
    Console --> Anomaly["Anomaly Index"]
    Console --> Explain["Top Feature Drivers"]
    Console --> Attention["Cross-Modal Attention Snapshot"]
    Console --> Evidence["Evidence + Limitations Panel"]
```

Current replay evidence:

| Scenario | State | Meaning |
| --- | --- | --- |
| Quiet Sun replay | NORMAL | Low probability and low anomaly, used to show non-alert behavior. |
| C-class watch replay | CRITICAL in current synthetic replay | Demonstrates event escalation and warning behavior. |
| M-class warning replay | CRITICAL | Demonstrates strong warning behavior. |
| X-class critical replay | CRITICAL | Demonstrates highest-risk replay state. |
| Background archive | QA-only | Contains non-curated rows and should not be used as the main judge demo. |

## 3. Repository And Artifact Structure

The repo is organized so the MVP can be rebuilt, verified, and explained from files instead of memory.

```mermaid
flowchart TD
    Root["Project Root"] --> App["app/streamlit_app.py"]
    Root --> Config["configs/mvp.yaml"]
    Root --> Src["src/arkanetra/"]
    Root --> Scripts["scripts/"]
    Root --> Data["data/processed/"]
    Root --> Reports["reports/"]
    Root --> Docs["docs/"]
    Root --> Tests["tests/"]

    Src --> Pipeline["pipeline.py"]
    Src --> Features["features.py"]
    Src --> Models["models.py"]
    Src --> Anomaly["anomaly.py"]
    Src --> DataModules["data/ adapters"]
    Src --> Torch["torch_models.py"]

    Scripts --> Build["build_mvp.py"]
    Scripts --> Verify["verify_mvp.py"]

    Reports --> Predictions["predictions/arkanetra_mvp_predictions.parquet"]
    Reports --> Metrics["metrics.csv"]
    Reports --> Events["event_summary.md"]
    Reports --> Manifest["artifact_manifest.json"]

    Docs --> Constitution["DOC-001 Constitution"]
    Docs --> Hardening["DOC-602 Milestone 1.1 Report"]
    Docs --> FullPlan["DOC-603 Full Implementation Plan"]
```

## 4. Data And Feature Workflow

The current MVP uses deterministic synthetic proxy replay data. This exists so the whole product can run immediately even before real GOES/RHESSI/Fermi data is integrated. The next milestone replaces at least one synthetic replay with a real GOES XRS event window.

```mermaid
flowchart TD
    A["Synthetic GOES/RHESSI-style proxy generator"] --> B["Raw soft_xray_flux + hard_xray_flux"]
    B --> C["Feature engineering"]
    C --> D["Hardness ratio"]
    C --> E["Soft X-ray derivative"]
    C --> F["Integrated hard X-ray energy"]
    C --> G["Waiting time since previous flare"]
    C --> H["Rolling mean / variance / slope / volatility"]
    D --> I["Processed dataset"]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J["Short-horizon flare labels"]
    J --> K["Chronological train / validation / test split"]
    K --> L["data/processed/arkanetra_mvp_dataset.parquet"]
```

Important rule: features must be computed from past and current data only. Future data must not leak into model inputs.

## 5. Model And Prediction Workflow

The Constitution calls for a Dual-Branch Cross-Attention GRU. The current runnable MVP uses an executable sklearn/numpy multimodal fusion surrogate because the local runtime did not initially include PyTorch. A PyTorch model boundary already exists in `src/arkanetra/torch_models.py` for the next implementation phase.

```mermaid
flowchart TD
    A["Processed dataset"] --> B["Baseline models"]
    A --> C["Soft-only model"]
    A --> D["Multimodal fusion surrogate"]

    D --> E["Cross-modal interaction score"]
    D --> F["Neupert consistency feature"]
    D --> G["Flare probability"]

    G --> H["Monte Carlo-style uncertainty"]
    H --> I["Confidence low / high"]
    G --> J["Alert state policy"]

    A --> K["PCA reconstruction anomaly surrogate"]
    K --> L["Anomaly index 0-100"]

    G --> M["Prediction record"]
    I --> M
    J --> M
    L --> M
    M --> N["reports/predictions/arkanetra_mvp_predictions.parquet"]
```

Current best generated demo model:

| Model | F1 | Precision | Recall | PR-AUC | ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| dual_branch_cross_attention_surrogate | 0.893 | 0.806 | 1.000 | 0.993 | 0.9997 |

## 6. Alert State Logic

The MVP converts model outputs into mission states using alert thresholds in `configs/mvp.yaml`.

```mermaid
flowchart TD
    A["Prediction row"] --> B["Flare probability"]
    A --> C["Anomaly index"]
    B --> D{"Probability >= critical threshold?"}
    D -->|Yes| Critical["CRITICAL"]
    D -->|No| E{"Probability >= warning threshold?"}
    E -->|Yes| Warning["WARNING"]
    E -->|No| F{"Probability >= watch threshold OR anomaly high?"}
    F -->|Yes| Watch["WATCH"]
    F -->|No| Normal["NORMAL"]
```

The current curated Quiet Sun replay stays NORMAL for all rows. That is important because the demo must show the system can avoid alerting under quiet conditions.

## 7. Dashboard Workflow

The dashboard does not train models live. It reads saved prediction artifacts. This makes the demo stable and reproducible.

```mermaid
sequenceDiagram
    participant Build as scripts/build_mvp.py
    participant Artifacts as Saved Reports + Predictions
    participant App as Streamlit Dashboard
    participant User as User/Judge

    Build->>Artifacts: Generate dataset, metrics, predictions, summaries
    App->>Artifacts: Load parquet, CSV, JSON evidence files
    User->>App: Select replay scenario
    App->>User: Show plots, risk, uncertainty, anomaly, explanations
    User->>App: Move replay position
    App->>User: Update mission state and evidence panels
```

Dashboard panels currently include:

- Mission status header.
- Replay scenario selector.
- Soft X-ray plot.
- Hard X-ray and hardness plot.
- Flare risk gauge.
- Confidence band.
- Anomaly index.
- Top feature drivers.
- Cross-modal attention snapshot.
- Model comparison table.
- Replay scenario summary.
- Evidence and limitations expander.

## 8. Verification And Evidence Workflow

The MVP now has a simple verification loop.

```mermaid
flowchart LR
    A["python scripts/build_mvp.py"] --> B["Generated artifacts"]
    B --> C["python -m pytest"]
    B --> D["python scripts/verify_mvp.py"]
    C --> E["Unit + smoke tests pass"]
    D --> F["Artifact and scenario checks pass"]
    E --> G["MVP accepted for demo"]
    F --> G
```

Current verification evidence:

- Test suite: `6 passed`.
- Verifier: `ArkaNetra MVP verification passed`.
- Dashboard: HTTP 200 on localhost port 8501.
- Prediction rows: 1728.
- Current scenarios: Quiet Sun, C-class, M-class, X-class, Background archive.

## 9. What Each Major Artifact Means

```mermaid
flowchart TD
    Dataset["arkanetra_mvp_dataset.parquet"] --> Meaning1["Processed features + labels + splits"]
    Predictions["arkanetra_mvp_predictions.parquet"] --> Meaning2["Dashboard-ready prediction records"]
    Metrics["metrics.csv"] --> Meaning3["Model comparison metrics"]
    EventSummary["event_summary.md"] --> Meaning4["Scenario-level demo evidence"]
    Manifest["artifact_manifest.json"] --> Meaning5["Artifact inventory + limitations + best model"]
    Verify["verify_mvp.py"] --> Meaning6["One-command package verification"]
    Dashboard["streamlit_app.py"] --> Meaning7["Mission-console interface"]
```

## 10. Phases Completed So Far

```mermaid
gantt
    title ArkaNetra Progress So Far
    dateFormat  YYYY-MM-DD
    section Foundation
    DOC-001 Constitution              :done, 2026-06-16, 1d
    MVP scaffold                      :done, 2026-06-16, 1d
    section MVP
    Synthetic proxy pipeline          :done, 2026-06-16, 1d
    Feature engineering               :done, 2026-06-16, 1d
    Baselines and fusion surrogate    :done, 2026-06-16, 1d
    Streamlit mission console         :done, 2026-06-16, 1d
    section Hardening
    Artifact manifest and summaries   :done, 2026-06-16, 1d
    Curated quiet replay              :done, 2026-06-16, 1d
    Verification script               :done, 2026-06-16, 1d
    Full phased implementation plan   :done, 2026-06-16, 1d
```

## 11. Current MVP To Final System Roadmap

The current MVP should evolve through these phases.

```mermaid
flowchart TD
    M11["Milestone 1.1: Demo-Hardened MVP"] --> P1["Phase 1: Real GOES XRS soft X-ray integration"]
    P1 --> P2["Phase 2: RHESSI or Fermi hard X-ray proxy integration"]
    P2 --> P3["Phase 3: PyTorch Dual-Branch Cross-Attention GRU"]
    P3 --> P4["Phase 4: GRU Autoencoder anomaly detection"]
    P4 --> P5["Phase 5: Research-grade evaluation and ablations"]
    P5 --> P6["Phase 6: Dashboard productization"]
    P6 --> P7["Phase 7: Aditya-L1 SoLEXS + HEL1OS integration"]
    P7 --> P8["Phase 8: Operational decision-support workflow"]
    P8 --> P9["Phase 9: SEP and radiation-risk extension"]
    P9 --> P10["Phase 10: Final full ArkaNetra platform"]
```

## 12. Future Full Architecture

This is the architecture ArkaNetra is moving toward, based on DOC-001.

```mermaid
flowchart TD
    A["Data Sources"] --> A1["GOES XRS proxy"]
    A --> A2["RHESSI / Fermi hard X-ray proxy"]
    A --> A3["Future SoLEXS"]
    A --> A4["Future HEL1OS"]

    A1 --> B["Unified Data Layer"]
    A2 --> B
    A3 --> B
    A4 --> B

    B --> C["Feature Engineering"]
    C --> C1["Soft X-ray flux"]
    C --> C2["Hard X-ray flux"]
    C --> C3["Hardness ratio"]
    C --> C4["d(SXR)/dt"]
    C --> C5["Integrated HXR energy"]
    C --> C6["Waiting time + rolling stats"]

    C --> D["Soft X-Ray GRU Encoder"]
    C --> E["Hard X-Ray GRU Encoder"]
    D --> F["Cross-Attention Fusion"]
    E --> F
    F --> G["Neupert Physics Constraint"]
    G --> H["Forecasting Head"]
    H --> I["Monte Carlo Dropout Uncertainty"]
    H --> J["Explainability Layer"]
    C --> K["GRU Autoencoder Anomaly Detector"]
    H --> L["Mission Dashboard"]
    I --> L
    J --> L
    K --> L
    L --> M["Operational Decision Support"]
```

## 13. Why This Workflow Matters

ArkaNetra is built around an operational question, not just a machine-learning question.

Most simple systems answer:

- Will a flare occur?

ArkaNetra is designed to answer:

- Will a flare occur?
- How confident are we?
- Why does the system believe this?
- Is the Sun behaving unusually?
- What mission or radiation-risk context should analysts watch?

```mermaid
mindmap
  root((ArkaNetra))
    Forecasting
      Flare probability
      Lead-time estimate
      Severity context
    Trust
      Confidence interval
      Uncertainty variance
      Calibration
    Physics
      Soft X-ray derivative
      Hard X-ray flux
      Neupert effect
    Explainability
      Top feature drivers
      Attention heatmap
      Event summaries
    Operations
      Mission state
      Alert thresholds
      Audit manifest
      Dashboard replay
    Future
      SoLEXS
      HEL1OS
      SEP risk
      Space-weather platform
```

## 14. What To Do Next

The next implementation step is Phase 1 from DOC-603:

1. Define the real GOES XRS data source.
2. Add GOES ingestion mode while keeping synthetic mode.
3. Curate one real GOES flare replay.
4. Preserve the current dashboard and prediction contract.
5. Regenerate reports and run the verifier.

This keeps the product moving from demo-hardened MVP toward a scientifically credible real-data prototype without breaking the working system we already have.

