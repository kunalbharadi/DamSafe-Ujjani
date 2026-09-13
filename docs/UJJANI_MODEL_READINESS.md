# Ujjani Dam — 16-Item Strict Model-Readiness Assessment

**Purpose:** Formal readiness gate evaluation for running a hydraulic simulation of the Bhima River reach downstream of Ujjani Dam. This assessment determines whether the assembled datasets, parameters, and boundary conditions are sufficient for a physically meaningful site simulation.

**Date:** September 2026
**Branch:** `feature/phase-5-ujjani-site-data`
**Evaluating Module:** [`readiness_gate.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/readiness_gate.py)
**Test Suite:** [`test_phase5a_site_readiness.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/tests/test_phase5a_site_readiness.py)

---

## Overall Verdict

```
╔══════════════════════════════════════════════════════════════════╗
║  UJJANI SITE MODEL READINESS:  NOT_READY_FOR_SITE_RUN          ║
║                                                                  ║
║  BLOCKING ITEMS:  3 (bathymetry, upstream forcing, downstream)   ║
║  PARTIAL ITEMS:   6                                              ║
║  PASS ITEMS:      7                                              ║
║                                                                  ║
║  Classification:  TERRAIN_APPROXIMATION_ONLY                     ║
║  Any simulation using current inputs MUST be labelled:           ║
║  "APPROXIMATE DEMONSTRATION — NOT VALIDATED SITE RUN"            ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 16-Item Readiness Matrix

| # | Input Category | Status | Evidence / Source | Limitation / Remaining Work |
|---|---|---|---|---|
| 1 | **Terrain / DEM** | ✅ PASS | Copernicus GLO-30 DEM (30 m, 1 arc-sec), GEE `COPERNICUS/DEM/GLO30` | Surface-only; vertical datum EGM96 geoid, not local gauge zero. Adequate for floodplain topography but not sub-channel resolution. |
| 2 | **Downstream Reach Geometry** | ✅ PASS | HydroRIVERS centerline (WWF/HydroSHEDS v1.0), 115 km Ujjani → Pandharpur | Reach length, bounding box `(74.60, 17.65, 75.95, 18.35)`, and valley slope (0.35 m/km) defined. |
| 3 | **Channel Bathymetry** | ❌ BLOCKED | No sub-surface riverbed survey available from public data | **CRITICAL BLOCKER.** Satellite DEMs capture water surface, not bed. Bankfull-depth approximation (3.5 m trapezoidal incision, 120 m bottom width) is a demonstrative placeholder only. Results using this approximation MUST NOT be certified as validated site simulations. |
| 4 | **Dam Specification** | ✅ PASS | CWC National Register of Large Dams, WRD Maharashtra | Crest 497.0 m, FRL 496.83 m, MWL 497.58 m, MDDL 491.03 m, 41 radial gates (12.19 m × 8.23 m). Codified in [`ujjani.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/ujjani.py). |
| 5 | **Storage Capacity** | ✅ PASS | CWC Register | Gross 3.14 km³ (117.24 TMC), Live 1.517 km³, Dead 1.623 km³. |
| 6 | **Gate Specifications** | ⚠️ PARTIAL | WRD Mechanical Division records | Gate dimensions verified (41 × 12.19 m × 8.23 m). Gate discharge rating curves (head-discharge relationship per gate) NOT available. Individual gate operation sequence during flood events NOT recorded. |
| 7 | **Upstream Boundary / Forcing** | ❌ BLOCKED | WRD district flood bulletins (digitized) | Aggregate release hydrograph available as coarse 3-hourly peaks for October 2020 event (~250,000 cusecs peak). Continuous hourly SCADA telemetry NOT available. Timezone assumed IST (not explicitly stated in bulletins). See `DISCHARGE_DIGITIZED_FROM_BULLETIN` uncertainty flag. |
| 8 | **Forcing Attribution** | ⚠️ PARTIAL | NWIC CKAN catalogue downloads (2 resources) | Raw CSV files preserved in `data/raw/`. Per-gate discharge columns present but: gate-to-physical-outlet mapping unknown; columns 45–50 mostly missing; missing values must NOT be summed as zero. Audit in `evidence/hydrology-audit.json`. |
| 9 | **Downstream Boundary** | ❌ BLOCKED | CWC Pandharpur gauge station | Gauge datum (443.2 m MSL) known. Full rating curve (stage-discharge) NOT available for flood range. Normal-depth assumption requires calibrated friction slope. |
| 10 | **Roughness / Friction** | ⚠️ PARTIAL | Literature values (Chow, 1959) | Manning's n: main channel 0.035, floodplain 0.055. These are textbook defaults for "clean, straight natural stream" and "agricultural fields" respectively. NOT calibrated to Bhima River conditions. Site-specific calibration requires at least one simulated-vs-observed flood comparison. |
| 11 | **Coordinate Reference System** | ✅ PASS | EPSG:4326 (WGS84) input → EPSG:32643 (UTM Zone 43N) solver domain | Projection verified with round-trip test in [`test_phase5a_site_readiness.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/tests/test_phase5a_site_readiness.py). Domain extents: X [670,000 – 810,000], Y [1,950,000 – 2,030,000] m. |
| 12 | **Vertical Datum** | ⚠️ PARTIAL | EGM96 Geoid (orthometric height above MSL) | DEM elevations referenced to EGM96. Dam operating levels referenced to "m MSL" (assumed EGM96-compatible). Local gauge zero at Pandharpur (443.2 m MSL) NOT independently verified against EGM96 datum. Potential systematic offset of 0.5–2.0 m if datum references differ. |
| 13 | **Temporal Reference / Clock** | ✅ PASS | IST (UTC+05:30) → UTC conversion implemented | `ist_to_utc()` converter in [`preprocessing.py`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/backend/damsafe/site/preprocessing.py). Satellite timestamps natively UTC. |
| 14 | **Permanent Water Baseline** | ✅ PASS | JRC Global Surface Water Occurrence v1.4 (30 m, 1984–2021) | Occurrence > 80% used as permanent water mask. Available via GEE `JRC/GSW1_4/GlobalSurfaceWater`. |
| 15 | **Historical Event Selection** | ⚠️ PARTIAL | October 2020 Bhima Flood selected as primary; August 2019 as secondary | Event timing, approximate peak discharge, and Sentinel-1 scene pairs identified. Full hourly forcing hydrograph NOT available. See [`UJJANI_EVENT_MANIFEST.md`](file:///c:/Users/kunal/OneDrive/Desktop/DAM/docs/UJJANI_EVENT_MANIFEST.md). |
| 16 | **Satellite Observation** | ⚠️ PARTIAL | ESA Copernicus Sentinel-1 GRD catalogue | Scene IDs identified and pair compatibility verified (same satellite, orbit, mode, polarization). No authentic scene processed or imported into DamSafe. GEE credentials unavailable for live processing. |

---

## Summary Statistics

| Status | Count | Items |
|---|---|---|
| ✅ PASS | 7 | Terrain, Reach, Dam, Storage, CRS, Clock, Permanent Water |
| ⚠️ PARTIAL | 6 | Gates, Forcing Attribution, Roughness, Vertical Datum, Event Selection, Satellite |
| ❌ BLOCKED | 3 | Bathymetry, Upstream Forcing, Downstream Boundary |

---

## Readiness Classification Definitions

| Classification | Meaning |
|---|---|
| `READY_FOR_VALIDATED_SITE_RUN` | All 16 items PASS. Simulation results may be presented as scientifically validated predictions for the Ujjani–Bhima reach. |
| `READY_FOR_APPROXIMATE_SITE_RUN` | No BLOCKED items. At least one PARTIAL item. Simulation may run but results MUST carry uncertainty disclaimers and MUST NOT be used for emergency operational decisions. |
| `NOT_READY_FOR_SITE_RUN` | One or more BLOCKED items. Simulation MUST NOT be executed as a site run. Software-only laboratory demonstrations may continue with synthetic data. |

**Current Classification: `NOT_READY_FOR_SITE_RUN`**

---

## Required Actions to Unblock

| Priority | Action | Required Source | Estimated Effort |
|---|---|---|---|
| 1 | **Obtain riverbed bathymetric survey** | WRD Maharashtra / CWPRS Pune cross-section surveys | Government data request + processing |
| 2 | **Obtain continuous discharge telemetry** | WRD SCADA system or CWC real-time data portal | Agency cooperation + data cleaning |
| 3 | **Obtain Pandharpur rating curve** | CWC Krishna Basin Organisation | Government data request |
| 4 | **Calibrate Manning's roughness** | Post-simulation calibration against observed flood extent | Requires items 1–3 first |
| 5 | **Verify vertical datum alignment** | Survey benchmark comparison (EGM96 vs local gauge zero) | Field survey or published benchmark tables |
| 6 | **Process authentic Sentinel-1 observation** | GEE credentials + live Earth Engine processing | Technical setup + computation |

---

## Relationship to Software Readiness

> [!IMPORTANT]
> **Software readiness ≠ Site model readiness.**
>
> The DamSafe application pipeline (project creation → dataset ingestion → readiness audit → scenario → solver run → normalization → products → comparison → export → observation) has been verified end-to-end with synthetic laboratory data in Phase 4 (14-stage E2E lineage test).
>
> This model-readiness assessment evaluates whether the **physical input data** for the Ujjani–Bhima site are sufficient for a scientifically meaningful hydraulic simulation. The software is ready; the site data are not.
