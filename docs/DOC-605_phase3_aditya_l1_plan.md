# DOC-605: Phase 3 — Aditya-L1 Payload Integration Prototype

**Project:** Project Solaris  
**Source:** DOC-601_MVP_to_Final_Version_Development_Plan.md  
**Current Baseline:** Phase 1 (GOES) + Phase 2 (RHESSI/Fermi) complete, 26 tests pass  
**Date:** 2026-06-16

---

## Objective

Shift from proxy-data demonstration (GOES/RHESSI/Fermi) to mission-aligned architecture (SoLEXS/HEL1OS). Preserve unified prediction schema, add provenance labels, and ensure the same pipeline handles both data modes.

---

## Guiding Constraints

1. Preserve DOC-001 Constitution and current working pipeline
2. Keep synthetic → proxy → Aditya-L1 mode progression intact
3. Do not break existing 26 tests or verify_mvp.py
4. Add SoLEXS/HEL1OS adapters with identical feature-pipeline compatibility
5. Dashboard must clearly display data source provenance in all modes
6. Explanations must use payload-aware terminology when appropriate

---

## Architecture Overview

```
data.mode = synthetic | goes_proxy | aditya_l1

For aditya_l1:
  data.aditya_l1.soft_source = solexs | solexs_sample
  data.aditya_l1.hard_source = hel1os | hel1os_sample
```

---

## Phase 3.1: SoLEXS Adapter (Soft X-Ray)

### Goal
Add SoLEXS adapter that maps payload channels into Solaris soft X-ray features.

### Step 3.1.1: Define SoLEXS Schema
**Tasks:**
- Research SoLEXS channel specifications (energy range, cadence, units, time format)
- Document expected input schema for SoLEXS payload data
- Add schema reference to `docs/`
- Update DOC-002 with SoLEXS schema decision

**Deliverables:**
- `docs/DOC-606_solexs_schema.md` — SoLEXS payload schema documentation
- Updated DOC-002 with schema decision

**Acceptance Criteria:**
- SoLEXS channel mapping documented
- Schema compatible with existing soft X-ray feature pipeline

### Step 3.1.2: Implement SoLEXS Adapter
**Tasks:**
- Create `src/solaris/data/solexs.py`
- Implement `load_solexs_csv(path)` — parse payload CSV into DataFrame
- Implement `download_solexs(start, end)` — fetch from ISRO archive or use bundled sample
- Normalize timestamps to UTC
- Map SoLEXS channels into `soft_xray_flux`
- Add quality flags (`ok`, `stale`, `suspect_high`, `invalid`)
- Add payload metadata columns: `soft_instrument`, `soft_payload_version`, `soft_channel`

**Deliverables:**
- `src/solaris/data/solexs.py`
- `data/raw/aditya_l1_sample/solexs_*.csv` — bundled sample data
- Unit tests for SoLEXS parsing

**Acceptance Criteria:**
- SoLEXS data can be loaded into DataFrame with `timestamp`, `soft_xray_flux`, `soft_source`
- Quality flags propagate correctly
- Payload metadata preserved

### Step 3.1.3: Add SoLEXS Sample Data
**Tasks:**
- Create synthetic SoLEXS sample CSV (realistic channel mapping)
- Include time, flux, energy bands, quality flags
- Store in `data/raw/aditya_l1_sample/`
- Update `config.py` with sample path constants

**Deliverables:**
- `data/raw/aditya_l1_sample/solexs_sample_20260101_20260102.csv`
- `data/raw/aditya_l1_sample/noaa_flare_catalog_solexs.csv`

**Acceptance Criteria:**
- Sample SoLEXS data loads correctly
- Pipeline can process sample in Aditya-L1 mode

---

## Phase 3.2: HEL1OS Adapter (Hard X-Ray)

### Goal
Add HEL1OS adapter for high-energy channel mapping with background handling and quality flags.

### Step 3.2.1: Define HEL1OS Schema
**Tasks:**
- Research HEL1OS channel specifications (energy range, cadence, units)
- Document expected input schema for HEL1OS payload data
- Update DOC-002 with HEL1OS schema decision

**Deliverables:**
- `docs/DOC-607_hel1os_schema.md` — HEL1OS payload schema documentation
- Updated DOC-002 with schema decision

**Acceptance Criteria:**
- HEL1OS channel mapping documented
- Schema compatible with existing hard X-ray feature pipeline

### Step 3.2.2: Implement HEL1OS Adapter
**Tasks:**
- Create `src/solaris/data/hel1os.py`
- Implement `load_hel1os_csv(path)` — parse payload CSV into DataFrame
- Implement `download_hel1os(start, end)` — fetch from ISRO archive or use bundled sample
- Normalize timestamps to UTC
- Map HEL1OS channels into `hard_xray_flux`
- Add background subtraction handling
- Add quality flags
- Add payload metadata columns: `hard_instrument`, `hard_payload_version`, `hard_energy_band`

**Deliverables:**
- `src/solaris/data/hel1os.py`
- `data/raw/aditya_l1_sample/hel1os_*.csv` — bundled sample data
- Unit tests for HEL1OS parsing

**Acceptance Criteria:**
- HEL1OS data loads into DataFrame with `timestamp`, `hard_xray_flux`, `hard_source`
- Background subtraction works correctly
- Payload metadata preserved

### Step 3.2.3: Add HEL1OS Sample Data
**Tasks:**
- Create synthetic HEL1OS sample CSV (realistic energy band mapping)
- Include time, flux, energy bands, background, quality flags
- Store in `data/raw/aditya_l1_sample/`

**Deliverables:**
- `data/raw/aditya_l1_sample/hel1os_sample_20260101_20260102.csv`

**Acceptance Criteria:**
- Sample HEL1OS data loads correctly
- Pipeline can process sample in Aditya-L1 mode

---

## Phase 3.3: Unified Pipeline Mode Switch

### Goal
Extend `data.mode` to support `aditya_l1` alongside `synthetic` and `goes_proxy`.

### Step 3.3.1: Update Config Schema
**Tasks:**
- Add `aditya_l1` as valid `data.mode` in `configs/mvp.yaml`
- Add `data.aditya_l1` section:
  - `soft_source`: `solexs` | `solexs_sample` | path to CSV
  - `hard_source`: `hel1os` | `hel1os_sample` | path to CSV
  - `payload_metadata`: boolean (include instrument metadata)
- Preserve backward compatibility with `synthetic` and `goes_proxy`

**Deliverables:**
- Updated `configs/mvp.yaml`
- Config validation in `config.py`

**Acceptance Criteria:**
- All three modes load without error
- Config schema validated

### Step 3.3.2: Implement Aditya-L1 Build Path
**Tasks:**
- Extend `solaris.data.goes` or create `solaris.data.aditya_l1.py`
- Route to SoLEXS/HEL1OS based on `data.aditya_l1` config
- Preserve unified prediction schema
- Preserve data provenance columns

**Deliverables:**
- Updated pipeline routing logic
- `build_aditya_l1_replay(config)` function
- Unified return: `(pd.DataFrame, pd.DataFrame)` with both soft and hard X-ray

**Acceptance Criteria:**
- `build_dataset(config)` works for all three modes
- Output DataFrame has same columns regardless of mode
- Provenance columns (`soft_source`, `hard_source`) populated correctly

### Step 3.3.3: Update Pipeline Provenance
**Tasks:**
- Extend `build_artifact_manifest` to include Aditya-L1 metadata
- Add `mission_mode` to manifest (`proxy` vs `aditya_l1`)
- Add `payload_metadata` dictionary with instrument details

**Deliverables:**
- Updated manifest schema
- Updated `pipeline.py` provenance logic

**Acceptance Criteria:**
- Manifest reflects correct mission mode
- Payload metadata present in Aditya-L1 runs

---

## Phase 3.4: Dashboard Provenance & Terminology

### Goal
Dashboard clearly displays source provenance and uses payload-aware terminology.

### Step 3.4.1: Add Provenance Panel
**Tasks:**
- Extend "Evidence & Limitations" panel in Streamlit dashboard
- Show `data_mode`, `soft_source`, `hard_source`, `mission_mode`
- Display payload metadata when available
- Differentiate proxy vs Aditya-L1 runs visually

**Deliverables:**
- Updated `app/streamlit_app.py`
- Provenance panel with mission-specific labels

**Acceptance Criteria:**
- Dashboard shows "Aditya-L1 Mode" when `data.mode=aditya_l1`
- Source instrument displayed (SoLEXS/HEL1OS vs GOES/RHESSI)
- Payload metadata visible in expanded panel

### Step 3.4.2: Update Explanation Terminology
**Tasks:**
- Replace generic "hard X-ray" with payload-aware terms when applicable
- SoLEXS mode: reference "soft X-ray channels" not "GOES"
- HEL1OS mode: reference "high-energy channels" not "RHESSI"
- Add mission context to dashboard explanations

**Deliverables:**
- Updated dashboard text templates
- Payload-aware explanation logic

**Acceptance Criteria:**
- Dashboard text references correct payload based on data mode
- No references to GOES/RHESSI when in Aditya-L1 mode

### Step 3.4.3: Update Dashboard Plots
**Tasks:**
- Add payload-specific plot titles when in Aditya-L1 mode
- Show channel energy ranges in plot legends
- Add mission context to plot annotations

**Deliverables:**
- Updated plot generation logic
- Payload-aware plot titles and labels

**Acceptance Criteria:**
- Plots reflect correct instrument names
- Energy bands displayed in legends

---

## Phase 3.5: Testing & Verification

### Step 3.5.1: Unit Tests for SoLEXS/HEL1OS
**Tasks:**
- Create `tests/test_solexs_adapter.py`
- Create `tests/test_hel1os_adapter.py`
- Test CSV loading, quality flags, resampling, provenance
- Test error handling for malformed data

**Deliverables:**
- `tests/test_solexs_adapter.py` — 6+ tests
- `tests/test_hel1os_adapter.py` — 6+ tests

**Acceptance Criteria:**
- All new tests pass
- Edge cases covered (empty files, missing columns, bad timestamps)

### Step 3.5.2: Integration Tests
**Tasks:**
- Extend `tests/test_artifacts.py` to include Aditya-L1 mode
- Test `run_mvp` with `data.mode=aditya_l1`
- Verify manifest, predictions, and reports generated correctly
- Verify dashboard can launch in Aditya-L1 mode

**Deliverables:**
- Updated `tests/test_artifacts.py`
- Aditya-L1 integration test

**Acceptance Criteria:**
- `pytest` passes all tests including new Aditya-L1 tests
- `verify_mvp.py` passes in Aditya-L1 mode

### Step 3.5.3: Documentation Updates
**Tasks:**
- Update `DOC-402_Task_Board.md` — mark Phase 3 tasks complete
- Update `DOC-002_Decision_Log.md` — add SoLEXS/HEL1OS decisions
- Create `docs/DOC-608_phase3_verification_report.md`

**Deliverables:**
- Updated task board
- Updated decision log
- Phase 3 verification report

**Acceptance Criteria:**
- All Phase 3 tasks marked complete
- Decisions documented

---

## Phase 3 Deliverables Checklist

| Deliverable | Status |
|-------------|--------|
| SoLEXS adapter (`src/solaris/data/solexs.py`) | Pending |
| HEL1OS adapter (`src/solaris/data/hel1os.py`) | Pending |
| SoLEXS sample data | Pending |
| HEL1OS sample data | Pending |
| Config schema update | Pending |
| Pipeline mode switch | Pending |
| Dashboard provenance panel | Pending |
| Dashboard terminology update | Pending |
| Unit tests for SoLEXS | Pending |
| Unit tests for HEL1OS | Pending |
| Integration tests | Pending |
| Documentation updates | Pending |

---

## Exit Criteria

Phase 3 is complete when ALL of the following are true:

1. **Same pipeline runs in proxy mode and Aditya-L1 mode**
   - `data.mode=synthetic` works
   - `data.mode=goes_proxy` works
   - `data.mode=aditya_l1` works

2. **Every prediction carries full metadata**
   - `source`: `GOES_XRS_REAL`, `SYNTHETIC`, `SOLEXS_REAL`
   - `instrument`: `GOES-XRS`, `SOLEXS`, `HEL1OS`
   - `config`: version, feature set
   - `model_version`: current model version
   - `generated_at`: UTC timestamp

3. **Dashboard defends Aditya-L1 dual-band observations**
   - Provenance panel shows correct payload
   - Explanations reference correct instruments
   - Plots display correct channel information

4. **All tests pass**
   - 26 existing tests remain green
   - New Aditya-L1 tests pass
   - `verify_mvp.py` passes

---

## Estimated Effort

| Step | Estimated Hours |
|------|-----------------|
| SoLEXS Adapter | 6-8 |
| HEL1OS Adapter | 6-8 |
| Config & Pipeline | 4-6 |
| Dashboard Updates | 4-6 |
| Testing | 6-8 |
| Documentation | 2-3 |
| **Total** | **28-39** |

---

## Risk Register Update

| Risk | Mitigation |
|------|------------|
| SoLEXS/HEL1OS schema unknown | Research ISRO payload docs; use synthetic sample |
| Payload data format changes | Abstract adapter behind common interface |
| Dashboard breaks in Aditya-L1 mode | Add integration test before merge |
| Backward compatibility lost | Run all three modes in CI |

---

## Next Steps After Phase 3

Phase 4: Operational Decision-Support Prototype  
- Watch/warning/critical alert policies
- Event summary generation
- Stale-data warnings
- Scenario comparison
- Prediction API

---

*Document created: 2026-06-16*
*Author: Solaris Development Agent*
*Reference: DOC-601 Phase 3*
