# DOC-606: SoLEXS Schema Reference

**Project:** Project Solaris  
**Date:** 2026-06-16

---

## Overview

SoLEXS (Solar Low-Energy X-ray Spectrometer) is the soft X-ray instrument aboard India's Aditya-L1 mission. This document defines the expected SoLEXS data schema for the Solaris pipeline.

---

## SoLEXS Instrument Characteristics

| Property | Value |
|----------|-------|
| Energy Range | 0.5 – 10 keV |
| Primary Channels | SXS (Soft X-ray Spectrometer), XRS (X-ray Spectrometer) |
| Cadence | ~1 second (telemetry), resampled to pipeline cadence (default 5 min) |
| Units | photons/cm²/s/keV or W/m² (flux normalized to GOES equivalent) |
| Time Format | UTC ISO 8601 |
| Data Format | CSV (converted from mission FITS/ASCII) |

---

## Input CSV Schema

The SoLEXS adapter accepts CSV files with the following columns:

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| `timestamp` | ISO 8601 datetime | Observation time in UTC | Yes |
| `soft_xray_flux` | float | Soft X-ray flux (normalized to GOES XRS long-channel equivalent) | Yes |
| `energy_band` | string | Energy band identifier (e.g., "1-8 keV") | Recommended |
| `data_quality` | string | Quality flag: `ok`, `stale`, `suspect_high`, `invalid` | Auto-generated |
| `solexs_channel` | string | Specific channel: `SXS`, `XRS-A`, `XRS-B` | Recommended |
| `exposure_time` | float | Integration time in seconds | Optional |
| `background_flag` | bool | True if background-subtracted | Optional |
| `payload_version` | string | Instrument firmware/software version | Optional |

---

## Quality Flags

| Flag | Meaning | Action |
|------|---------|--------|
| `ok` | Data within normal range | Use as-is |
| `stale` | Flux < 1e-10 (quiet Sun floor) | Use with caution; may indicate detector off |
| `suspect_high` | Flux > 1e-2 (saturation or particle event) | Flag for review |
| `invalid` | NaN, zero, or missing | Exclude from feature computation |

---

## Mapping to Solaris Schema

SoLEXS data is mapped to the Solaris soft X-ray schema:

```
SoLEXS timestamp        →  Solaris timestamp
SoLEXS soft_xray_flux   →  Solaris soft_xray_flux
SoLEXS energy_band      →  Solaris soft_channel (metadata)
SoLEXS data_quality      →  Solaris data_quality
SoLEXS SXS/XRS channel   →  Solaris soft_instrument = "SOLEXS"
```

---

## Sample SoLEXS Data

Sample data for 2026-01-01 to 2026-01-02 is stored at:
```
data/raw/aditya_l1_sample/solexs_sample_20260101_20260102.csv
```

---

## Known Limitations

1. SoLEXS is not yet launched/operational; sample data is synthetic but schema-realistic
2. Energy band mapping to GOES XRS equivalent requires cross-calibration (future work)
3. Background subtraction may vary by channel; flag indicates if applied

---

## References

- Aditya-L1 Mission: ISRO
- SoLEXS Instrument: TBD (placeholder until instrument paper published)
- Related: GOES XRS (soft X-ray proxy reference)

---

*Last Updated: 2026-06-16*