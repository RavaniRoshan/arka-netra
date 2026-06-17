# Phase 1 GOES XRS Data Source

## Source

- **Provider:** NOAA Space Weather Prediction Center (SWPC)
- **URL:** `https://services.swpc.noaa.gov/json/goes/`
- **Endpoint:** `https://services.swpc.noaa.gov/json/goes/primary/xray-7-day.json`
- **Format:** JSON array of objects with `time_tag` and `flux` fields per channel
- **Documentation:** https://www.swpc.noaa.gov/products/goes-x-ray-flux

## Channels

| Channel | Wavelength | ArkaNetra Mapping | Used? |
| ------- | ---------- | --------------- | ----- |
| Long (L) | 1-8 Angstrom | `soft_xray_flux` | Yes |
| Short (S) | 0.5-4.0 Angstrom | Not used in Phase 1 | No |

## Cadence

- Native: 1 minute
- Pipeline cadence: 5 minutes (resampled with forward fill)

## Units

- `soft_xray_flux`: Watts per square metre (W/m²)
- 1 X-class increment = 1-8 × 10⁻⁴ W/m²

## Known Caveats

1. The SWPC JSON API only provides the last 7 days of data.
2. For historical events (e.g., 2017-09-06 X9.3), use the bundled sample CSV at `data/raw/goes_sample/`.
3. GOES data has occasional gaps during satellite eclipse seasons and sensor maintenance.
4. Sensor degradation causes subtle calibration drift over multi-year periods.
5. The SWPC endpoint may have brief outages; the bundled sample CSV always works.

## Fallback

A bundled sample CSV is included at `data/raw/goes_sample/goes_xrs_20170905_20170907.csv` covering the 2017-09-06 X9.3 flare event (48-hour window). This file is the default when `data.goes_source: auto` and the download fails.

## Sample Event

- **Event:** X9.3 flare on 2017-09-06
- **Peak time:** ~12:02 UTC
- **Preceded by:** X2.2 flare at ~09:00 UTC same day
- **Also includes:** surrounding C/M-class activity
