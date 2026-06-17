# DOC-601: MVP To Final-Version Development Plan

## Current MVP Baseline

The current workspace contains a runnable replay-first MVP. It generates deterministic GOES/RHESSI-style proxy data, computes the mandatory physics-inspired features, creates short-horizon flare labels, trains baseline models, trains an executable multimodal fusion surrogate, computes uncertainty and anomaly index, exports parquet artifacts, and serves a Streamlit mission console.

The MVP is intentionally honest about its limits. It proves the system contract, dashboard flow, evaluation shape, and documentation spine. It does not yet prove operational forecasting performance because it uses synthetic proxy data. The next phases replace the synthetic generator with real proxy datasets and then integrate Aditya-L1 payload data.

## Phase 1: Hardening The Hackathon MVP

Objective: make the demo reliable enough for judging.

Implementation work:

- Replace synthetic replay intervals with curated GOES XRS event windows and one hard X-ray proxy source.
- Keep synthetic data as a smoke-test fixture.
- Add a command that builds all artifacts from one clean entrypoint.
- Persist model metadata, feature config, data provenance, and split definition beside every prediction file.
- Capture dashboard screenshots for quiet, watch, warning, and critical states.
- Expand reports with baseline comparison, soft-only vs multimodal ablation, physics-loss off/on ablation, uncertainty distribution, and lead-time examples.

Exit criteria:

- A new evaluator can run setup, build artifacts, launch the dashboard, and complete the demo script without manual repair.
- Every claim in the presentation maps to a metric, plot, or documented limitation.

## Phase 2: Real Proxy Data Research Prototype

Objective: make the system scientifically meaningful with public data.

Implementation work:

- Build robust GOES XRS ingestion with cadence normalization, missing-data flags, and flare-class alignment.
- Integrate RHESSI first if feasible; otherwise integrate Fermi GBM as the hard X-ray proxy.
- Implement event-based dataset construction so train, validation, and test splits do not leak event context.
- Add multi-horizon labels, at minimum short nowcast and longer watch windows.
- Replace the sklearn fusion surrogate with the PyTorch DualBranchCrossAttentionGRU in `src/arkanetra/torch_models.py`.
- Implement GRU autoencoder anomaly detection instead of the current PCA reconstruction proxy.
- Add calibration metrics and threshold policy tuning.

Exit criteria:

- Multimodal fusion is compared against soft-only and hard-only baselines.
- Neupert loss is evaluated with a clear ablation.
- Uncertainty is evaluated for calibration and operational usefulness.
- A technical report can defend the system without relying on synthetic performance.

## Phase 3: Aditya-L1 Payload Integration Prototype

Objective: shift from proxy-data demonstration to mission-aligned architecture.

Implementation work:

- Add SoLEXS adapter with payload metadata, cadence handling, quality flags, and soft X-ray channel mapping.
- Add HEL1OS adapter with high-energy channel mapping, background handling, and quality flags.
- Preserve a unified prediction schema across proxy mode and Aditya-L1 mode.
- Add dashboard provenance labels so every replay clearly states GOES/RHESSI/Fermi or SoLEXS/HEL1OS.
- Update explanations to use payload-aware terminology.

Exit criteria:

- The same pipeline can run in proxy mode and Aditya-L1 mode.
- Every prediction carries source, instrument, config, model version, and generated-at metadata.
- The dashboard can defend why Aditya-L1 dual-band observations are central to the project.

## Phase 4: Operational Decision-Support Prototype

Objective: move from demo to analyst workflow.

Implementation work:

- Add watch, warning, and critical alert policies with configurable thresholds.
- Add event summary generation, analyst notes, and audit logs.
- Add stale-data and missing-data warnings.
- Add scenario comparison for multiple events and model versions.
- Add an API endpoint or file-based service contract for prediction records.
- Add reliability tests for ingestion failures, empty windows, missing hard X-ray data, and uncertain predictions.

Exit criteria:

- An analyst can understand state, risk, confidence, anomaly, explanation, and source provenance in one workflow.
- Every alert can be traced back to data, model, config, and threshold policy.
- False alarm and missed-event tradeoffs are visible and configurable.

## Phase 5: Space-Weather Platform

Objective: evolve ArkaNetra from flare warning into broader mission-risk support.

Implementation work:

- Add validated SEP-risk modeling with particle data and separate evaluation.
- Add satellite-risk and human-spaceflight radiation context modules.
- Add forecast archive, alert subscriptions, model drift checks, monitoring, and retraining workflows.
- Add release process, versioned model registry, and operating handbook.
- Prepare publication and pilot-collaboration materials.

Exit criteria:

- ArkaNetra supports flare risk, anomaly detection, uncertainty, explanation, and radiation-risk context without unsupported claims.
- The system is credible for research collaboration or an operational pilot discussion.
- Documentation is complete enough for a new science and engineering team to continue development.

## Phase 6: Final Full-Version Platform

Objective: bring ArkaNetra from hackathon demonstrator to a credible research-grade, operationally-oriented platform aligned with DOC-001 Constitution Part X product stages.

### Phase 6.1: Real Data Validation

Goal: prove the full pipeline works on real GOES+RHESSI data, not just synthetic proxies.

Implementation work:

- Download and curate multi-event GOES XRS dataset covering at least 3 major flare events (C/M/X class) from 2017 Sep (Solar Cycle 24 peak).
- Download matching RHESSI hard X-ray data for the same events.
- Run the full pipeline (ingestion → features → sklearn training → predictions → alerts) on real data end-to-end.
- Validate that real-data predictions produce meaningful probability curves (not flat zeros or ones).
- Verify hardness ratio, derivative, and Neupert-consistency features are physically plausible on real data.
- Export real-data replay scenarios into the dashboard schema.
- Add a `data.mode: real_proxy` config option that loads real GOES+RHESSI data instead of synthetic.

Exit criteria:

- Pipeline runs on real data without manual repair.
- Real-data predictions show physically meaningful flare probability evolution.
- Dashboard can replay real flare events with soft X-ray, hard X-ray, and hardness plots.
- All 79+ existing tests still pass.

### Phase 6.2: GRU Hardening

Goal: make the PyTorch GRU architecture a first-class, tested, production-ready model path.

Implementation work:

- Install PyTorch in the CI/test environment and add `torch` to test dependencies.
- Train `DualBranchCrossAttentionGRU` on real GOES+RHESSI data end-to-end.
- Validate Neupert loss trains correctly and loss curve is stable.
- Add GRU-specific tests: sequence shape validation, checkpoint save/load round-trip, inference consistency.
- Add `GRUModel` to the comparison table in the evaluation report.
- Verify GRU autoencoder anomaly detection works on real quiet-Sun intervals.
- Add `model.architecture: gru` as a first-class tested path (not just opt-in).

Exit criteria:

- GRU model trains on real data and produces calibrated probabilities.
- GRU checkpoint save/load round-trips without accuracy loss.
- GRU anomaly detection produces meaningful anomaly indices on real events.
- GRU path has dedicated test coverage.

### Phase 6.3: Evaluation & Ablations

Goal: make ArkaNetra defensible as a research prototype with comprehensive metrics and ablation studies.

Implementation work:

- Add event-based train/validation/test splits (no event context leakage across splits).
- Implement calibration metrics: Brier score, expected calibration error (ECE), reliability diagram data.
- Implement comprehensive classification metrics: ROC-AUC, PR-AUC, confusion matrix per flare class.
- Implement lead-time analysis: time from first warning threshold crossing to catalog event onset.
- Implement false alarm analysis: false alarm rate, mean false alarm duration.
- Automate ablation studies: soft-only, hard-only, concatenation fusion, cross-attention fusion, physics-loss on/off.
- Generate ablation comparison table as CSV and Markdown.
- Add `scripts/run_evaluation.py` entry point for full evaluation suite.

Exit criteria:

- Evaluation report includes Brier score, ECE, ROC-AUC, PR-AUC, lead time, and false alarm rate.
- Ablation table shows soft-only vs hard-only vs multimodal vs cross-attention performance.
- Physics-loss on/off ablation is documented with interpretation.
- Event-based splits prevent temporal leakage.

### Phase 6.4: Dashboard Productization

Goal: turn the dashboard into a mission-control style decision-support interface per DOC-001 Part X.

Implementation work:

- Add analysis mode: deep-dive view for a selected event showing raw signals, engineered features, attention heatmap, anomaly reconstruction, Neupert consistency, and prediction evolution.
- Add model comparison mode: side-by-side comparison of sklearn vs GRU predictions on the same event.
- Add multi-horizon display: show predictions for multiple forecast windows (e.g., 30min, 60min, 120min) simultaneously.
- Add event summary export: Markdown and CSV export of event summary (probability peak, anomaly peak, first warning time, lead time, top drivers, source provenance).
- Add threshold policy selector: allow analyst to switch between conservative, balanced, and sensitive alert thresholds from the dashboard.
- Polish existing replay mode with clearer provenance labels.

Exit criteria:

- A judge can understand mission state in under one minute.
- A technical reviewer can inspect features, attention, anomaly, uncertainty, and model comparison.
- Event summaries are exportable as Markdown/CSV.
- Threshold policy can be changed from the dashboard.

### Phase 6.5: Release Process

Goal: make ArkaNetra installable, reproducible, and deployable.

Implementation work:

- Add `fastapi` and `uvicorn` to `pyproject.toml` dependencies.
- Add Dockerfile for containerized deployment.
- Add `docker-compose.yml` for local development (API + dashboard).
- Add GitHub Actions CI workflow: lint, test, build.
- Add `Makefile` or `justfile` for common commands (test, lint, build, serve).
- Add `.dockerignore` and `.github/workflows/ci.yml`.
- Add `CHANGELOG.md` for version tracking.
- Tag version `v1.0.0` as the first stable release.

Exit criteria:

- `pip install -e .[dev]` installs all dependencies including PyTorch.
- `docker build` produces a working container.
- CI runs lint + tests on every push.
- A new developer can clone, install, test, and run the dashboard without manual repair.

### Phase 6.6: Documentation Completion

Goal: complete the documentation hierarchy defined in DOC-001 Appendix A.

Implementation work:

- Create DOC-614: Phase 6 Verification Report (following DOC-610/DOC-613 format).
- Update DOC-601: append Phase 6 to the development plan.
- Update DOC-002: record all Phase 6 decisions.
- Update DOC-402: mark all Phase 6 tasks complete.
- Update DOC-403: close resolved risks, add new risks if any.
- Verify all existing documentation is consistent with Phase 6 changes.

Exit criteria:

- DOC-614 verification report documents Phase 6 exit criteria met.
- DOC-002 decision log is up to date.
- DOC-402 task board reflects current state.
- A new team member can understand the full system from documentation alone.

