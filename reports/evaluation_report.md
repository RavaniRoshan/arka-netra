# Project Solaris MVP Evaluation Report

## Baseline And Model Comparison

| model | precision | recall | f1 | pr_auc | roc_auc | brier_score | ece | false_alarm_rate | true_negative | false_positive | false_negative | true_positive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_forest_baseline | 1 | 0.58 | 0.7342 | 0.9201 | 0.9384 | 0.04555 | 0.1772 | 0 | 662 | 0 | 21 | 29 |
| soft_only_logistic | 0.5735 | 0.78 | 0.661 | 0.4377 | 0.9568 | 0.08448 | 0.1914 | 0.04381 | 633 | 29 | 11 | 39 |
| dual_branch_cross_attention_surrogate | 0.9 | 0.9 | 0.9 | 0.9818 | 0.9986 | 0.008102 | 0.009042 | 0.007553 | 657 | 5 | 5 | 45 |

## Current Best MVP Model

The highest F1 row is `dual_branch_cross_attention_surrogate` with F1=0.900, precision=0.900, recall=0.900.

**Brier Score**: 0.0081 (lower is better)

**ECE**: 0.0090 (lower is better)

**False Alarm Rate**: 0.0076

## Lead-Time Check

Median warning lead time on labeled warning rows: 55.0 minutes. Range: 0.0 - 120.0 minutes.

## Limitations

This MVP uses deterministic synthetic proxy data to make the full pipeline runnable immediately. Real GOES/RHESSI/Fermi data adapters are scaffolded, and the final-version plan covers mission-data integration.
