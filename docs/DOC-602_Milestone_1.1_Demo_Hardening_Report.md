# DOC-602: Milestone 1.1 Demo Hardening Report

## Status

Milestone 1.1 upgrades the first Project Solaris MVP from a working scaffold into a more defensible demo package.

## Improvements Completed

- Added explicit alert policy thresholds in `configs/mvp.yaml`.
- Added artifact manifest with row counts, best-model metrics, known limitations, and generated file evidence.
- Added event summary reports in CSV and Markdown.
- Added curated replay scenario assignment so the Quiet Sun demo remains genuinely normal.
- Added dashboard metric cards, scenario ordering, evidence expander, and background-archive warning.
- Fixed anomaly-index reconstruction math in the PCA autoencoder surrogate.
- Added `scripts/verify_mvp.py` for one-command artifact verification.

## Current Evidence

- Quiet Sun replay: NORMAL for all rows.
- Event replay scenarios: C, M, and X class windows all escalate to warning/critical states.
- Best generated demo model: dual-branch cross-attention surrogate.
- Test suite: `6 passed`.

## Remaining Limitations

- Synthetic proxy replay data is still used for immediate reproducibility.
- The PyTorch GRU model is scaffolded but not yet the active training path.
- Real GOES/RHESSI/Fermi ingestion is the next milestone.

## Next Milestone

Milestone 1.2 should replace at least one synthetic event window with a real public GOES XRS window and preserve the same dashboard/prediction contract.

