# DOC-402: Project Solaris Task Board

## Done

- Create DOC-001 Constitution.
- Create executable MVP scaffold.
- Generate sample proxy dataset and prediction artifacts.
- Build Streamlit replay dashboard.
- Add unit and smoke tests.
- Add MVP-to-final roadmap.
- Complete Milestone 1.1 demo hardening with artifact manifest, event summary, curated quiet replay, dashboard evidence panel, and verifier.
- Create DOC-603 current-MVP-to-final full-version phased implementation plan.
- Create `explanation.md` visual workflow explainer for the current MVP and future path.

## Done

- Integrate real GOES XRS download path (Phase 1).
- Integrate RHESSI + Fermi hard X-ray subset (Phase 2).
- Implement Aditya-L1 SoLEXS + HEL1OS adapters (Phase 3).
- Add unified pipeline mode switch (`aditya_l1`).
- Add dashboard provenance panel and payload-aware terminology.
- Phase 3 documentation: DOC-605, DOC-606, DOC-607, DOC-608.
- Phase 4 complete: Alert lifecycle, audit log, staleness detection, FastAPI endpoint, reliability tests.
- Phase 4 documentation: DOC-609.

## Done

- Implement Space-Weather Platform (Phase 5):
  - Add validated SEP-risk modeling with particle data and separate evaluation.
  - Add satellite-risk and human-spaceflight radiation context modules.
  - Add forecast archive, alert subscriptions, model drift checks, monitoring, and retraining workflows.
  - Add release process, versioned model registry, and operating handbook.
  - Prepare publication and pilot-collaboration materials.
- Phase 5 documentation: DOC-610, DOC-611, DOC-612, DOC-613.

## Done

- Implement Final Full-Version Platform (Phase 6):
  - Real data validation with GOES+RHESSI.
  - GRU hardening with PyTorch CI.
  - Comprehensive evaluation with calibration metrics, lead-time analysis, ablations.
  - Dashboard productization with analysis mode, model comparison, multi-horizon, event summary export, threshold policy selector.
  - Release process with Dockerfile, docker-compose, GitHub Actions CI, Makefile, CHANGELOG.md.
  - Documentation completion with DOC-614 verification report.
- Phase 6 documentation: DOC-614.

## Backlog (Future)

- Event-based dataset construction (Phase 2).
- Multi-horizon labels (Phase 2).
- Calibration metrics (Phase 2).
- Threshold policy tuning (Phase 2).
- Scenario comparison (Phase 4).
- Reliability tests (Phase 4).
