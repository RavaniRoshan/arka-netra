# ArkaNetra MVP To Final-Version Development Plan

## Version 1.1: Stronger Hackathon MVP

- Replace synthetic replay intervals with curated real GOES plus RHESSI/Fermi event windows.
- Add experiment tracking, exported event summaries, presentation-ready plots, and dashboard screenshots.
- Expand ablations across threshold baseline, soft-only model, multimodal model, and physics-loss variants.

## Version 1.5: Research Prototype

- Build a multi-year event dataset with chronological and event-based validation.
- Add multi-horizon prediction, severity classification, calibration, missing-data handling, and hyperparameter search.
- Prepare a technical report answering multimodal value, Neupert-loss value, anomaly-index timing, and uncertainty reliability.

## Version 2.0: Aditya-L1 Integration Prototype

- Add SoLEXS and HEL1OS ingestion adapters with payload metadata, cadence normalization, and data-quality checks.
- Keep proxy mode and Aditya-L1 mode in the same pipeline with explicit provenance in every prediction record.
- Update dashboard labels and explanations to be payload-aware.

## Version 2.5: Operational Decision-Support Prototype

- Add watch/warning/critical alert policy, threshold configuration, analyst notes, audit logs, and event summaries.
- Provide an API endpoint for prediction records and scenario comparison.
- Track model version, config, source data, and alert rationale for every warning.

## Version 3.0: Space-Weather Platform

- Add validated SEP-risk modeling with particle data and radiation-context workflows.
- Add satellite-risk and human-spaceflight mission context modules.
- Add forecast archive, subscription alerts, monitoring, drift checks, and continuous retraining.
