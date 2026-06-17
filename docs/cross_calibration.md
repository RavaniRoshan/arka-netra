# Aditya-L1 Cross-Calibration Documentation

**Project:** Project Solaris  
**Date:** 2026-06-17  
**Status:** Phase 7 — Experimental

---

## Overview

This document describes the cross-calibration methodology used to compare Aditya-L1 instrument data (SoLEXS, HEL1OS) with established solar observatories (GOES XRS, RHESSI, Fermi GBM).

**Disclaimer:** All cross-calibration results are experimental and derived from limited overlapping data. They are not validated against official calibration standards and should not be used for operational decision-making without independent validation.

---

## Instruments

### Aditya-L1

| Instrument | Full Name | Energy Range | Measurement |
|-----------|-----------|-------------|-------------|
| **SoLEXS** | Solar X-ray Sensor | 0.3–3 keV | Soft X-ray flux |
| **HEL1OS** | High Energy X-ray Spectrometer | 25–100 keV | Hard X-ray flux |

### Reference Instruments

| Instrument | Mission | Energy Range | Measurement |
|-----------|---------|-------------|-------------|
| **GOES XRS** | GOES-R series | 0.05–0.1 nm (short), 0.1–0.8 nm (long) | Soft X-ray flux |
| **RHESSI** | Reuven Ramaty High Energy Solar Spectroscopic Imager | 3 keV – 17 MeV | Hard X-ray/gamma-ray counts |
| **Fermi GBM** | Fermi Gamma-ray Burst Monitor | 8 keV – 40 MeV | Hard X-ray/gamma-ray counts |

---

## Cross-Calibration Method

### Log-Space Linear Regression

Both cross-calibrations use log-space linear regression:

```
log10(Aditya) = α × log10(Reference) + β
```

Where:
- `α` = spectral index (slope)
- `β` = offset
- **Gain factor** = 10^α

### Metrics

| Metric | Description |
|--------|-------------|
| **Correlation coefficient** | Pearson correlation between log-transformed fluxes |
| **Gain factor** | 10^α — ratio of Aditya to reference instrument response |
| **RMS residual** | Root mean square of residuals from the fit |
| **Overlapping points** | Number of co-temporal data points used |

---

## SoLEXS vs GOES XRS

### Method

1. Load SoLEXS soft X-ray flux (0.3–3 keV)
2. Load GOES XRS long-wavelength flux (0.1–0.8 nm)
3. Merge on timestamp with nearest-neighbor matching (5-minute tolerance)
4. Filter to positive, finite values
5. Apply log10 transform
6. Fit linear regression: `log10(SoLEXS) = α × log10(GOES) + β`

### Expected Behavior

- SoLEXS and GOES XRS observe overlapping energy ranges in soft X-rays
- Correlation should be high (>0.8) for co-temporal data
- Gain factor <1.0 indicates SoLEXS has lower effective area than GOES XRS

### Limitations

- Energy band mismatch: SoLEXS (0.3–3 keV) vs GOES XRS (0.05–0.8 nm ≈ 0.15–25 keV)
- Different detector responses and calibration states
- SOLEXS is at L1 (1 AU), GOES is in GEO (35,786 km) — different viewing geometry

---

## HEL1OS vs RHESSI/Fermi

### Method

1. Load HEL1OS hard X-ray flux (25–100 keV)
2. Load reference instrument flux (RHESSI or Fermi GBM)
3. Merge on timestamp with nearest-neighbor matching (5-minute tolerance)
4. Filter to positive, finite values
5. Apply log10 transform
6. Fit linear regression: `log10(HEL1OS) = α × log10(Reference) + β`

### Expected Behavior

- HEL1OS and RHESSI/Fermi observe overlapping energy ranges in hard X-rays
- Correlation should be moderate to high (>0.7) during flare events
- Gain factor indicates relative sensitivity

### Limitations

- RHESSI is decommissioned (2002–2018) — only archival data available
- Fermi GBM is a burst detector, not optimized for continuous solar monitoring
- Different energy band definitions and detector responses

---

## Usage

```python
from solaris.data.cross_calibration import (
    cross_calibrate_solexs_vs_goes,
    cross_calibrate_hel1os_vs_reference,
    generate_calibration_report,
)

# Load data
solexs_df = ...  # SoLEXS data
goes_df = ...    # GOES XRS data
hel1os_df = ...  # HEL1OS data
rhessi_df = ...  # RHESSI data

# Cross-calibrate
solexs_cal = cross_calibrate_solexs_vs_goes(solexs_df, goes_df)
hel1os_cal = cross_calibrate_hel1os_vs_reference(hel1os_df, rhessi_df, reference_instrument="RHESSI")

# Generate report
report = generate_calibration_report(solexs_cal, hel1os_cal)
```

---

## Validation Status

| Calibration | Status | Notes |
|------------|--------|-------|
| SoLEXS vs GOES | **Experimental** | Requires overlapping operational data |
| HEL1OS vs RHESSI | **Experimental** | RHESSI archived data only |
| HEL1OS vs Fermi | **Experimental** | Requires co-temporal Fermi GBM data |

---

## Future Work

1. **Official calibration comparison**: Validate gain factors against ISRO/GOES calibration documents
2. **Time-dependent calibration**: Track gain factor evolution over mission lifetime
3. **Energy-resolved calibration**: Compare at specific energy channels rather than broadband
4. **Cross-normalization**: Apply calibration factors to harmonize Aditya-L1 and GOES data streams
