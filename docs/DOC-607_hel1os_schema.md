# DOC-607: HEL1OS Schema Reference

**Project:** Project Solaris  
**Date:** 2026-06-16

---

## Overview

HEL1OS (HELiospheric LOw-energy Spectrometer) is the hard X-ray instrument aboard India's Aditya-L1 mission. This document defines the expected HEL1OS data schema for the Solaris pipeline.

---

## HEL1OS Instrument Characteristics

| Property | Value |
|----------|-------|
| Energy Range | 3 – 150 keV (primary), up to 1 MeV (extended) |
| Primary Channels | Multiple overlapping bands (e.g., 3-6, 6-12, 12-25, 25-50, 50-100 keV) |
| Cadence | ~1 second (telemetry), resampled to pipeline cadence (default 5 min) |
| Units | photons/cm²/s/keV or normalized count rate |
| Time Format | UTC ISO 8601 |
| Data Format | CSV (converted from mission FITS/ASCII) |

---

## Input CSV Schema

The HEL1OS adapter accepts CSV files with the following columns:

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| `timestamp` | ISO 8601 datetime | Observation time in UTC | Yes |
| `hard_xray_flux` | float | Hard X-ray flux (normalized to RHESSI equivalent) | Yes |
| `energy_band` | string | Energy band (e.g., "25-100 keV") | Recommended |
| `data_quality` | string | Quality flag: `ok`, `stale`, `suspect_high`, `invalid` | Auto-generated |
| `hel1os_channel` | string | Specific channel identifier | Recommended |
| `background_subtracted` | bool | True if background removed | Optional |
| `background_level` | float | Estimated background level | Optional |
| `exposure_time` | float | Integration time in seconds | Optional |
| `payload_version` | string | Instrument firmware/software version | Optional |

---

## Quality Flags

| Flag | Meaning | Action |
|------|---------|--------|
| `ok` | Data within normal range | Use as-is |
| `stale` | Flux < 1e-12 (near instrumental background) | Use with caution |
| `suspect_high` | Flux > 1e-1 (saturation or particle event) | Flag for review |
| `invalid` | NaN, negative, or missing | Exclude from feature computation |

---

## Mapping to Solaris Schema

HEL1OS data is mapped to the Solaris hard X-ray schema:

```
HEL1OS timestamp        →  Solaris timestamp
HEL1OS hard_xray_flux   →  Solaris hard_xray_flux
HEL1OS energy_band      →  Solaris hard_energy_band (metadata)
HEL1OS data_quality     →  Solaris data_quality
HEL1OS channel          →  Solaris hard_instrument = "HEL1OS"
```

The pipeline normalizes HEL1OS to RHESSI-equivalent flux to maintain feature compatibility.

---

## Sample HEL1OS Data

Sample data for 2026-01-01 to 2026-01-02 is stored at:
```
data/raw/aditya_l1_sample/hel1os_sample_20260101_20260102.csv
```

---

## Background Handling

HEL1OS uses a rolling background estimation:
1. Quiet-Sun intervals identified (flux near instrumental floor)
2. Background level computed as median of quiet intervals
3. `hard_xray_flux_corrected = hard_xray_flux - background_level`
4. Negative values after subtraction set to 0

---

## Known Limitations

1. HEL1OS is not yet launched/operational; sample data is synthetic but schema-realistic
2. Energy band mapping to RHESSI equivalent requires cross-calibration (future work)
3. Background subtraction algorithm is placeholder; real algorithm TBD

---

## References

- Aditya-L1 Mission: ISRO
- HEL1OS Instrument: TBD (placeholder until instrument paper published)
- Related: RHESSI (hard X-ray proxy reference)

---

*Last Updated: 2026-06-16*