# Ujjani Dam — 16-Item Strict Model-Readiness Assessment

**Purpose:** Formal readiness gate evaluation for running a hydraulic simulation of the Bhima River reach downstream of Ujjani Dam. This assessment determines whether the assembled datasets, parameters, and boundary conditions are sufficient for a physically meaningful site simulation.

**Date:** September 2026
**Branch:** `feature/phase-5b-ujjani-hydraulic-run`
**Evaluating Module:** [`readiness_gate.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/readiness_gate.py)
**Test Suites:** [`test_phase5a_site_readiness.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/tests/test_phase5a_site_readiness.py), [`test_phase5b_hydraulic_run.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/tests/test_phase5b_hydraulic_run.py)
**Execution Report:** [`UJJANI_FIRST_RUN_REPORT.md`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/docs/UJJANI_FIRST_RUN_REPORT.md)

---

## Overall Verdict

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  UJJANI SITE MODEL READINESS:                                                ║
║                                                                              ║
║  Strict Mode (default):       NOT_READY_FOR_SITE_RUN (1 BLOCKED: Bathymetry) ║
║  Approximate Mode (Phase 5B): READY_FOR_APPROXIMATE_SITE_RUN                 ║
║                                                                              ║
║  MANDATORY BLOCKERS COUNT:    0 (under documented TERRAIN_APPROXIMATION)     ║
║  PARTIAL ITEMS:               7                                              ║
║  PASS ITEMS:                  9                                              ║
║                                                                              ║
║  Classification:              UJJANI_APPROXIMATE_DEMONSTRATION               ║
║  Any simulation using current inputs MUST be labelled:                       ║
║  "APPROXIMATE DEMONSTRATION — NOT VALIDATED SITE RUN"                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 16-Item Readiness Matrix

| # | Input Category | Status | Evidence / Source | Limitation / Remaining Work |
|---|---|---|---|---|
| 1 | **Terrain / DEM** | ✅ PASS | Copernicus GLO-30 DEM (30 m, 1 arc-sec), GEE `COPERNICUS/DEM/GLO30` | Surface-only; vertical datum EGM96 geoid. Adequate for floodplain topography but not sub-channel resolution. |
| 2 | **Downstream Reach Geometry** | ✅ PASS | HydroRIVERS centerline (WWF/HydroSHEDS v1.0), 115 km Ujjani → Pandharpur | Reach length, bounding box `(74.60, 17.65, 75.95, 18.35)`, and valley slope (0.35 m/km) defined. |
| 3 | **Channel Bathymetry** | ⚠️ PARTIAL (Approx) / ❌ BLOCKED (Strict) | `TERRAIN_ONLY_CHANNEL_APPROXIMATION` incised trapezoidal channel (3.5 m depth, 120 m width) below DEM | Sub-surface soundings unperformed. Permitted ONLY for `UJJANI_APPROXIMATE_DEMONSTRATION`; blocks validated historical runs. |
| 4 | **Dam Specification** | ✅ PASS | CWC National Register of Large Dams, WRD Maharashtra | Crest 497.0 m, FRL 496.83 m, MWL 497.58 m, MDDL 491.03 m, 41 radial gates (12.19 m × 8.23 m). Codified in [`ujjani.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/ujjani.py). |
| 5 | **Storage Capacity** | ✅ PASS | CWC Register | Gross 3.14 km³ (117.24 TMC), Live 1.517 km³, Dead 1.623 km³, Area 337 km². |
| 6 | **Gate Specifications** | ✅ PASS | WRD Mechanical Division records | Gate dimensions verified (41 × 12.19 m × 8.23 m, Ogee crest spillway). |
| 7 | **Upstream Initial State** | ⚠️ PARTIAL | NWIC daily reservoir levels and aggregate storage state | Sub-hourly inflow series requires hydrological routing. |
| 8 | **Forcing / Release Hydrograph** | ⚠️ PARTIAL | WRD district flood bulletins (digitized for 14–22 Oct 2020) | Coarse 3-hourly/daily series (~250,000 cusecs peak). Continuous hourly SCADA telemetry unverified. |
| 9 | **Downstream Boundary** | ⚠️ PARTIAL | CWC Pandharpur gauge station (datum 443.2 m MSL) | Normal depth / constant stage approximation used. Full stage-discharge rating curve requires field survey. |
| 10 | **Roughness / Friction** | ⚠️ PARTIAL | Literature values (Chow, 1959) | Manning's n: main channel 0.035, floodplain 0.055. Textbook defaults; requires site calibration. |
| 11 | **Coordinate Reference System** | ✅ PASS | EPSG:4326 (WGS84) input → EPSG:32643 (UTM Zone 43N) solver domain | Projection verified with round-trip test in [`test_phase5a_site_readiness.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/tests/test_phase5a_site_readiness.py). |
| 12 | **Vertical Datum** | ⚠️ PARTIAL | EGM96 Geoid (orthometric height above MSL) | DEM elevations referenced to EGM96. Local gauge zero at Pandharpur requires geodetic tie to EGM96. |
| 13 | **Temporal Reference / Clock** | ✅ PASS | IST (UTC+05:30) → UTC conversion implemented | `ist_to_utc()` converter in [`preprocessing.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/preprocessing.py). Satellite timestamps natively UTC. |
| 14 | **Permanent Water Baseline** | ✅ PASS | JRC Global Surface Water Occurrence v1.4 (30 m, 1984–2021) | Occurrence > 80% used as permanent water mask for Ujjani reservoir. |
| 15 | **Historical Event Selection** | ✅ PASS | October 2020 Bhima Flood (14–22 Oct 2020) and August 2019 event defined | Event timing and digitized hydrograph codified in [`hydraulic_case.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/hydraulic_case.py). |
| 16 | **Satellite Observation** | ✅ PASS | ESA Copernicus Sentinel-1 GRD Relative Orbit 63 pair identified | Scene IDs and pair compatibility verified. |

---

## Summary Statistics

| Mode | PASS Items | PARTIAL Items | BLOCKED Items | Verdict |
|---|---|---|---|---|
| **Strict Evaluation** | 9 | 6 | 1 | `NOT_READY_FOR_SITE_RUN` |
| **Approximate Demonstration (Phase 5B)** | 9 | 7 | 0 | `READY_FOR_APPROXIMATE_SITE_RUN` |

---

## Readiness Classification Definitions

| Classification | Meaning |
|---|---|
| `READY_FOR_HISTORICAL_SITE_RUN` | All 16 items PASS with field verification. Simulation results may be presented as scientifically validated historical predictions. |
| `READY_FOR_APPROXIMATE_SITE_RUN` | 0 BLOCKED items under documented approximations (e.g. `TERRAIN_ONLY_CHANNEL_APPROXIMATION`). Simulation may run but results MUST carry uncertainty disclaimers. |
| `NOT_READY_FOR_SITE_RUN` | One or more BLOCKED items under strict evaluation without approximation acknowledgment. |

---

## Actions Required to Reach Historical Validation

1. **Obtain riverbed bathymetric survey:** WRD Maharashtra / CWPRS Pune cross-section surveys.
2. **Obtain continuous discharge telemetry:** WRD SCADA system or CWC real-time telemetry.
3. **Obtain Pandharpur rating curve:** CWC Krishna Basin Organisation stage-discharge curve.
4. **Calibrate Manning roughness:** Post-simulation calibration against observed flood high-water marks.
5. **Verify vertical datum alignment:** Survey benchmark comparison between EGM96 geoid and local gauge zero.
