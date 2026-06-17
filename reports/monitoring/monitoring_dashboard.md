# ArkaNetra Monitoring Dashboard

Generated: 2026-06-17T09:43:37.818880+00:00

## Overall Health: [OK] HEALTHY (score: 100/100)

### Issues

- Auto-retrain disabled (manual mode)

## Drift Monitoring

- **Drift Threshold**: 0.15
- **Retrain Mode**: manual
- **Total Cycles**: 11
- **Consecutive Drifts**: 0
- **Last Retrain**: None

## Validation Status

- **Total Validations**: 11
- **Mean F1**: 0.9045
- **Pass Rate**: 100.0%
- **F1 Range**: 0.9045 - 0.9045

## Recent Monitoring Cycles

| Time | Drift | Retrain | Validation | Duration |
| --- | --- | --- | --- | --- |
| 2026-06-17T09:34:05 | no | no | PASS | 0.0s |
| 2026-06-17T09:34:52 | no | no | PASS | 0.0s |
| 2026-06-17T09:35:38 | no | no | PASS | 0.0s |
| 2026-06-17T09:36:29 | no | no | PASS | 0.0s |
| 2026-06-17T09:43:37 | no | no | PASS | 0.0s |

## Limitations

- Monitoring operates on synthetic proxy data.
- Auto-retrain requires `retrain_trigger: auto` in config.
- Continuous validation requires a baseline model to compare against.
