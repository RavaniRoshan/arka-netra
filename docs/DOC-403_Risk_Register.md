# DOC-403: ArkaNetra Risk Register

| Risk | Status | Mitigation |
| --- | --- | --- |
| Real hard X-ray proxy data may take longer than expected. | Closed | RHESSI implemented as primary hard X-ray proxy with Fermi GBM fallback; real-data validation completed. |
| Model may overfit small event samples. | Mitigated | Event-based splits implemented, baselines and ablations added, real data validation completed. |
| Physics loss can be overclaimed. | Mitigated | Neupert loss implemented as soft inductive bias with ablations; clearly documented as physics constraint, not universal truth. |
| SEP panel can imply unsupported forecasts. | Controlled | SEP risk module implemented as experimental with clear disclaimers; labeled as future extension until particle data validation. |
| Dashboard scope can distract from core warning flow. | Controlled | Replay console focuses on risk, confidence, anomaly, and explanation; Phase 6 added analysis mode for deeper inspection. |
| PyTorch dependency not in CI. | Closed | Added to pyproject.toml dev dependencies; GRU hardening completed. |
| Real data validation complexity. | Mitigated | Implemented with fallback to synthetic data; validation pipeline tested. |
| Documentation consistency. | Mitigated | All updates tracked in DOC-002 decision log; DOC-614 verification report created. |
| Dashboard scope creep. | Controlled | Phase 6 added only required modes (analysis, model comparison, multi-horizon, event summary export, threshold policy selector). |
| Release process completeness. | Mitigated | Dockerfile, docker-compose, GitHub Actions CI, Makefile, CHANGELOG.md all created and validated. |

