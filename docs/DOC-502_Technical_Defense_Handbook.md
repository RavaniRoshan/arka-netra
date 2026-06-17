# DOC-502: Technical Defense Handbook

## MVP Architecture

Data enters as proxy soft and hard X-ray time series. The pipeline computes physics-inspired features, labels short-horizon flare risk, applies chronological splits, trains baselines, trains a multimodal fusion surrogate, estimates uncertainty, computes anomaly index, and exports replay predictions to the dashboard.

## Current Model Status

The executable MVP uses sklearn and NumPy to approximate the planned Dual-Branch Cross-Attention GRU behavior. It includes cross-modal interaction, Neupert consistency, uncertainty sampling, and an attention snapshot. The next ML milestone is a PyTorch GRU implementation.

## Evaluation Defense

The MVP reports baseline comparison, soft-only comparison, final model metrics, confusion matrix fields, lead-time examples, and limitation notes. The important defense is not that synthetic data proves operational performance; it proves the full system contract is working and ready for real proxy data.

