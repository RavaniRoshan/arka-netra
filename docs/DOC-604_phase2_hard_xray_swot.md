# DOC-604: Phase 2 Hard X-Ray Proxy Design — SWOT

## Dual-Usage Strategy: RHESSI Bundled CSV + Fermi GBM Live/FITS

## Context

Solaris Phase 2 requires real hard X-ray flux to make the multimodal fusion meaningful. The architecture supports two sources simultaneously:

1. **RHESSI** — primary bundled dataset + optional FITS download (astropy)
2. **Fermi GBM** — live CTIME/CSPEC FITS download (astropy)

Both sources feed a single `build_hard_xray_data()` entry point in `solaris/data/hard_xray_proxy.py`, with the same output contract: `timestamp + hard_xray_flux + data_quality`.

---

## SWOT Matrix

| | **Internal** | **External** |
|---|---|---|
| **Positive** | **S — Strengths** | **O — Opportunities** |
| | RHESSI is the canonical solar hard X-ray mission; its data quality and temporal resolution (4s) are unrivaled for this era. | Fermi GBM remains active (not decommissioned), enabling real-time or near-real-time demo capability after Phase 1. |
| | Bundled RHESSI CSV guarantees workspace reproducibility — no network dependency, no FITS parsing friction. | Fermi GBM daily CTIME/CSPEC files are reliably mirrored at HEASARC; `astropy.io.fits` handles them natively. |
| | The `hard_source` config switch (`auto/rhessi/fermi/none`) lets any two experts disagree and still share results. | Federation: RHESSI coverage for pre-2018 + Fermi coverage for 2008–present gives ~20 years of continuous hard X-ray context. |
| | A single `build_hard_xray_data()` contract keeps the rest of the pipeline (`goes.py`, `pipeline.py`, features, models, dashboard`) unchanged. | Both sources can coexist in the same replay: use RHESSI as ground truth, Fermi as backup, or blend by instrument availability. |
| | | |
| **Negative** | **W — Weaknesses** | **T — Threats** |
| | RHESSI was decommissioned 2018; no new data exists. For future operations, RHESSI alone is insufficient. | Fermi GBM CTIME/CSPEC FITS files are larger than RHESSI observing summaries; per-day download is ~20–50 MB. |
| | RHESSI observing summary FITS format varies by solarSoft version; astropy's generic reader may need tweaks for column names above `hsi_obssumm_dbase`. | Fermi GBM "observing summary" analog does not exist; must reconstruct lightcurve from spectrometer bins, adding processing risk. |
| | Bundling a CSV sample for RHESSI adds a ~500 KB–2 MB artifact that must be regenerated manually when a new event is curated. | HEASARC FTP/HTTP sometimes throttles or returns HTML error pages; the `urllib` download code paths need robust fallback logging. |
| | Fermi GBM data requires selecting a single detector (n0–n11); SUNWARD pointing is not guaranteed for all time slots. | RHESSI twilight/night gaps and Fermi SAA passages create overlapping but non-identical coverage — cross-calibration is non-trivial. |

---

## Threat Mitigation

| Threat | Mitigation |
|--------|-----------|
| RHESSI decommissioned | Fermi GBM is the active fallback; config `hard_source: fermi` is always valid. |
| Fermi GBM large files | CTIME (8-channel, 0.256s) is far smaller than CSPEC (128-channel, 4.096s). Adapter defaults to CTIME. |
| HEASARC throttling | Fallback to bundled CSV is automatic. Download scripts surface warnings but never block pipeline runs. |
| Detector selection uncertainty | Adapter defaults to detector `n5` (canonical SUNWARD); users can override via config. |
| FITS column name drift | Adapter tolerates absent bands by summing all `*keV*` columns as last-resort fallback; logs a warning. |

---

## Design Decision Summary

| Decision | Chosen Approach | Rationale |
|----------|-----------------|-----------|
| Primary hard X-ray source for replay demos | RHESSI bundled CSV | No network dependency; deterministic; covers 2017-09-06 event |
| Live download path | Fermi GBM CTIME via HEASARC | Mission-active; reliable daily files; simple URL pattern |
| FITS reader | `astropy.io.fits` | Standard library; handles both RHESSI and GBM formats |
| Uniform output contract | `timestamp, hard_xray_flux, data_quality, hard_source` | Downstream features, models, and dashboard remain source-agnostic |
| Header | `data_source` col in DataFrame | Allows one replay to carry both sources simultaneously if needed |
