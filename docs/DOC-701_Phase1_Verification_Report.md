# DOC-701: Phase 1 Verification Report

**Project:** ArkaNetra  
**Phase:** 1 — Real Data Ingestion Hardening  
**Date:** 2026-06-17  
**Status:** COMPLETE

---

## Verification Summary

| Metric | Result |
|--------|--------|
| Total Tests | 89 |
| Passed | 89 |
| Failed | 0 |
| Skipped | 0 |
| Warnings | 3 (expected — network-dependent) |
| Existing tests preserved | ✅ |

---

## Exit Criteria Verification

### 1. GOES SWPC Download Works

| Requirement | Status |
|-------------|--------|
| Correct URL (`xrays-7-day.json` vs old `xray-7-day.json`) | ✅ Fixed |
| Retry logic with exponential backoff | ✅ Implemented |
| Primary + secondary URL fallback (7-day → 1-day) | ✅ Implemented |
| Live data downloads without auth | ✅ Verified |
| Falls back to bundled sample CSV on failure | ✅ Preserved |
| Schema correctly parses `energy` field for channel filtering | ✅ Implemented |
| Short-channel filtering via `_is_short_channel()` | ✅ Verified |

### 2. Fermi GBM Download Path

| Requirement | Status |
|-------------|--------|
| `download_fermi_gbm_data()` implemented | ✅ Implemented |
| Downloads CSPEC + CTIME FITS files from HEASARC | ✅ Implemented |
| Detector selection (n5 default) | ✅ Implemented |
| `_parse_fermi_fits()` for EBOUNDS-based channel selection | ✅ Implemented |
| Graceful no-data fallback (warn, return empty list) | ✅ Verified |

### 3. Download Utility Module

| Requirement | Status |
|-------------|--------|
| `src/arkanetra/data/download.py` created | ✅ Created |
| `fetch_json()` with retry | ✅ Implemented |
| `fetch_binary()` with retry | ✅ Implemented |
| 404 short-circuits retry (no unnecessary retries) | ✅ Implemented |
| Max retries = 3, delay = 2s geometric | ✅ Implemented |

### 4. Data Provenance

| Requirement | Status |
|-------------|--------|
| GOES soft_source distinguishes live vs sample | ✅ `GOES_XRS_LIVE` / `GOES_XRS_SAMPLE` |
| `data.mode=goes_source=sample` explicit mode | ✅ Added |
| All predictions carry `soft_source` provenance | ✅ Verified |

### 5. Retry and Error Handling

| Requirement | Status |
|-------------|--------|
| Network timeout handled gracefully | ✅ Verified in test |
| HTTP 404 handled gracefully | ✅ Verified in test |
| JSON decode failure handled gracefully | ✅ Verified in test |
| All data modes survive network failures | ✅ Verified |

---

## Files Modified

| File | Change |
|------|--------|
| `src/arkanetra/data/goes.py` | Fixed SWPC URL, added retry, schema parsing, `sample` source mode, provenance labels |
| `src/arkanetra/data/hard_xray_proxy.py` | Added Fermi GBM download, FITS parser, refactored RHESSI download to use fetch_binary, cleaned imports |
| `src/arkanetra/data/download.py` | **New:** utility module with `fetch_json()`, `fetch_binary()` |
| `tests/test_download.py` | **New:** 10 tests for download utilities, GOES live download, Fermi GBM download |
| `tests/test_goes_adapter.py` | Updated assertions for new source labels, changed test to use `sample` mode |
| `tests/test_hard_xray_proxy.py` | Updated tests to use `sample` mode for consistent sample data |
| `tests/test_artifacts.py` | Updated goes mode test to use `sample` source |
| `docs/DOC-700_Grand_Unified_Implementation_Plan.md` | **New:** Master execution plan |

---

## Implementation Checklist

### Phase 1.1: GOES SWPC Download Fix
- [x] Fix URL from `xray-7-day.json` to `xrays-7-day.json`
- [x] Add `SWPC_XRAY_1DAY_URL` fallback
- [x] Add `_fetch_swpc_json()` with retry and URL fallback
- [x] Fix schema parsing (`energy` field instead of `channel`)
- [x] Add `_is_short_channel()` filter
- [x] Add `sample` source mode for tests
- [x] Add provenance labels (`GOES_XRS_LIVE` / `GOES_XRS_SAMPLE`)

### Phase 1.2: Download Utility
- [x] `src/arkanetra/data/download.py` created
- [x] `fetch_json()` with retry
- [x] `fetch_binary()` with retry
- [x] `save_csv()` utility

### Phase 1.3: Fermi GBM Support
- [x] `download_fermi_gbm_data()` implemented
- [x] `_parse_fermi_fits()` for CSPEC/CTIME parsing
- [x] `load_fermi_gbm_from_csv()` for sample data
- [x] `build_hard_xray_data()` updated to try Fermi GBM

### Phase 1.4: Test Hardening
- [x] All existing 79 tests preserved
- [x] 10 new tests for download utilities
- [x] Test for live GOES download
- [x] Test for Fermi GBM download (graceful no-data)
- [x] Test for retry logic via mock
- [x] Test for short-channel filtering
- [x] Source label assertion updates

---

## Known Limitations

1. **Fermi GBM live download**: HEASARC FTP may be unavailable in sandboxed environments. The function gracefully returns an empty list with a warning if download fails. Full FITS parsing requires `astropy` which is not always available in test environments.
2. **SWPC live download**: The endpoint requires internet access. Tests use `sample` mode to avoid network dependency for deterministic results.
3. **Live vs sample overlap**: Live GOES data (current 7 days) does not overlap with bundled RHESSI sample (2017-09-05 to 2017-09-07). Hard X-ray is zero-filled when downloading live GOES without matching RHESSI data. This is expected behavior for real-time mode.

---

## Phase 1 Summary

All exit criteria met. The GOES download path is fixed and verified. Fermi GBM infrastructure is in place (download and FITS parsing), though live HEASARC data is not validated end-to-end in this environment. The download utility module provides reusable retry logic for all future network operations. All 89 tests pass.
