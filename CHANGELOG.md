# Changelog

All notable changes to ArkaNetra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 6 implementation plan: real data validation, GRU hardening, evaluation & ablations, dashboard productization, release process, documentation completion
- FastAPI and uvicorn dependencies for API service
- Docker containerization support
- GitHub Actions CI workflow
- Makefile for common commands
- Analysis mode and model comparison mode to dashboard
- Multi-horizon forecast display
- Event summary export (Markdown/CSV)
- Threshold policy selector
- Real data validation pipeline
- GRU-specific tests and checkpointing
- Comprehensive evaluation metrics (Brier score, ECE, ROC-AUC, PR-AUC, lead time)
- Event-based train/validation/test splits
- Automated ablation studies

### Changed
- Updated pyproject.toml with optional dev dependencies
- Added `data.mode: real_proxy` configuration option
- Updated DOC-601 with Phase 6 development plan

## [0.1.0] - 2026-06-16

### Added
- ArkaNetra MVP: physics-informed multimodal solar flare early warning replay demo
- Synthetic proxy data generator (GOES/RHESSI-style)
- 12 physics-inspired features (hardness ratio, derivatives, volatility, waiting time, etc.)
- Multimodal fusion surrogate (sklearn)
- Monte Carlo uncertainty output
- PCA reconstruction-based anomaly index
- Streamlit mission dashboard
- Event summary and artifact manifest
- One-command MVP verifier
- Documentation (DOC-001 through DOC-613)
- Alert lifecycle with 6 states
- Audit and provenance tracking
- SEP/radiation risk context (experimental)
- Model registry
- Forecast archive
- Monitoring and drift detection
- FastAPI prediction API

### Changed
- Initial release of ArkaNetra MVP

## [0.0.1] - 2026-06-16

### Added
- Initial prototype and hackathon preparation

### Changed
- Initial development phase