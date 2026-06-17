# Solaris Monitoring Dashboard

Generated: 2026-06-17T05:54:15.246141+00:00

## Overall Health: [OK] HEALTHY (score: 100/100)

### Issues

- Auto-retrain disabled (manual mode)

## Drift Monitoring

- **Drift Threshold**: 0.15
- **Retrain Mode**: manual
- **Total Cycles**: 1
- **Consecutive Drifts**: 0
- **Last Retrain**: None

## Validation Status

- **Total Validations**: 1
- **Mean F1**: 0.9045
- **Pass Rate**: 100.0%
- **F1 Range**: 0.9045 - 0.9045

## Recent Monitoring Cycles

| Time | Drift | Retrain | Validation | Duration |
| --- | --- | --- | --- | --- |
| 2026-06-17T05:54:15 | no | no | PASS | 0.0s |

## Limitations

- Monitoring operates on synthetic proxy data.
- Auto-retrain requires `retrain_trigger: auto` in config.
- Continuous validation requires a baseline model to compare against.
