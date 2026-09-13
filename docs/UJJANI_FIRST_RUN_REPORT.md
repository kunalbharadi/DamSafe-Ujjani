# Ujjani Dam & Bhima River — D-Flow FM Site Run & Dynamics Report

**Date:** September 2026  
**Branch:** `feature/phase-5b-ujjani-hydraulic-run`  
**Execution Status:** `SUCCEEDED` (Exit Code 0)  
**Model Classification:** `UJJANI_APPROXIMATE_DEMONSTRATION`  
**Engine:** Deltares D-Flow FM (via DIMR sequential runner in bounded Docker container)  
**Solver Image:** `damsafe-dflowfm:local` (`sha256:d439312899ce18fc3c498355b3c87ddda55a59b3b74e762bc2b08425b2980cd8`)  

---

## 1. Executive Summary

Phase 5B established the end-to-end hydraulic simulation and analysis pipeline for the Ujjani Dam to Pandharpur reach of the Bhima River (115 km reach, UTM Zone 43N / EPSG:32643) using Deltares D-Flow FM:

1. **Phase 5B.1 (Integration Milestone):** Executed the first persistent D-Flow FM site run (`a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a`) proving software lifecycle integration, database persistence, NetCDF normalization, derived product generation, and independent export verification.
2. **Phase 5B.2 (Hydraulic Dynamics Milestone):** Executed a hydraulic dynamics audit to resolve boundary disconnection and static backwater issues, refactored boundary condition syntax to `ExtForceFileNew`, implemented dynamic polyline boundary snapping and sloping initial water levels, and executed the first genuine dynamic flood-wave run (`a8bacdd4-490c-4961-a8c1-a3a2d4e3874b`).

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  SIMULATION CLASSIFICATION:  UJJANI_APPROXIMATE_DEMONSTRATION               ║
║                                                                              ║
║  Readiness Gate Verdict:     READY_FOR_APPROXIMATE_SITE_RUN                 ║
║  Physical Status:            APPROXIMATE (5 unverified physical parameters) ║
║  Dynamic Run Velocity:       0.00 to 7.55 m/s (mean 2.01 m/s)                ║
║  Mass Conservation Error:    0.000004% (-102.0 m³ on 2.34 billion m³ inflow) ║
║  Timesteps Simulated:        217 intervals across 9-day flood progression   ║
║  Cells / Grid Dimension:     80 cells / 115 km curvilinear reach            ║
║                                                                              ║
║  CRITICAL NOTICE:                                                            ║
║  This run is an APPROXIMATE DEMONSTRATION utilizing a terrain-only channel   ║
║  approximation and digitized flood bulletins. It MUST NOT be presented as    ║
║  a validated historical simulation or used for emergency release operations. ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Persistent Runs Provenance Comparison

| Parameter | Phase 5B.1 (Initial Static) | Phase 5B.2 (Dynamic Wave) |
|---|---|---|
| **Run ID** | `a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a` | `a8bacdd4-490c-4961-a8c1-a3a2d4e3874b` |
| **Project ID** | `ujjani-persistent-proj-001` | `ujjani-persistent-proj-001` |
| **Scenario ID** | `ujjani-persistent-scen-001` | `ujjani-persistent-scen-002` |
| **Configuration Hash** | `f564ec64a5c3111c8ed8c773dbc6ddea347f5eda1a6a75476bd65b0e22459cab` | `3b8b16140617be60d17dfc484c07eb3a38c3d1fd4f91ccc68412c3f227ed1187` |
| **Boundary Mechanism** | Legacy `ExtForceFile` (unbound) | Modern `ExtForceFileNew` + Dynamic Polylines |
| **Initial Condition** | Flat `WaterLevIni = 492.0 m` | Sloping `initial_water_level.xyz` (bed + 1.5 m) |
| **Depth Range** | 6.50 m to 54.25 m (mean 30.71 m) | 0.46 m to 9.83 m (mean 5.60 m) |
| **Velocity Range** | 0.00 m/s to 1.29e-11 m/s | 0.00 m/s to 7.55 m/s (mean 2.01 m/s) |
| **Flood Peak Arrival** | N/A (static) | Dam Toe: 72h, Mid: 74h, Pandharpur: 75h |
| **Mass Balance Residual** | 0.0 m³ (static) | -102.0 m³ (0.000004% error on 2.34B m³ inflow) |
| **GeoTIFF Rasterization** | 1D Strip ($80 \times 1$) | True 2D Raster ($111 \times 216$ cells, 200m res) |
| **Classification** | `UJJANI_APPROXIMATE_DEMONSTRATION` | `UJJANI_APPROXIMATE_DEMONSTRATION` |

---

## 3. Persistent File Lineage & Checksums (Phase 5B.2 Run)

| Artifact Type | File Path | Status |
|---|---|---|
| **Solver Log** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/solver.log` | Complete solver trace preserved |
| **DIMR Configuration** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/dimr_config.xml` | Preserved |
| **Model Definition (MDU)** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/dflowfm/ujjani_bhima.mdu` | Preserved (`ExtForceFileNew`) |
| **Native 2D Map NetCDF** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/dflowfm/DFM_OUTPUT_ujjani_bhima/ujjani_bhima_map.nc` | Preserved |
| **Native History NetCDF** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/dflowfm/DFM_OUTPUT_ujjani_bhima/ujjani_bhima_his.nc` | Preserved |
| **Normalized Result NetCDF** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/normalized.nc` | Schema Version 1 Verified |
| **Derived Products NetCDF** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/products.nc` | Schema Version 2 Verified |
| **Input Manifest JSON** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/input-manifest.json` | Complete Provenance |
| **Diagnostics JSON** | `.local/runs/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b/diagnostics.json` | Mass balance & audit verified |

---

## 4. Flood-Wave Dynamics & Wave Celerity

The October 2020 flood wave hydrograph was routed through the 115 km reach with realistic hydrodynamic attenuation and lag:

```
+-----------------------------------------------------------------------------------------+
| Station                 Chainage   Peak Stage Time   Peak Depth   Peak Velocity   Status|
+-----------------------------------------------------------------------------------------+
| Ujjani Dam Toe (US)        0 km        t = 72.0 h      6.44 m       7.55 m/s      Active|
| Quarter-Reach             29 km        t = 73.0 h      8.11 m       3.02 m/s      Active|
| Mid-Reach                 58 km        t = 74.0 h      8.51 m       2.67 m/s      Active|
| Three-Quarter Reach       86 km        t = 75.0 h      8.83 m       2.64 m/s      Active|
| Pandharpur (DS)          115 km        t = 75.0 h      8.57 m       2.80 m/s      Active|
+-----------------------------------------------------------------------------------------+
```

Wave propagation celerity along the reach averaged $\approx 38.3\text{ km/h}$, consistent with open-channel flood wave theory for shallow water equations under steep discharge gradient.

---

## 5. Global Mass Conservation

$$\int Q_{\text{in}} dt = 2,344,334,592\text{ m}^3$$
$$\int Q_{\text{out}} dt = 2,342,132,480\text{ m}^3$$
$$\Delta \text{Storage} = 2,202,010\text{ m}^3$$
$$\text{Residual} = -102\text{ m}^3 \quad (4.35 \times 10^{-6}\% \text{ relative error})$$

---

## 6. Independently Reopened Exports (Phase 5B.2 Run)

All 6 export formats generated from `a8bacdd4-490c-4961-a8c1-a3a2d4e3874b` were independently reopened and verified:

| Format | Output Path | Verification Status | Properties |
|---|---|---|---|
| **GeoTIFF** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-geotiff.tif` | ✅ Verified | EPSG:32643, $111 \times 216$ cells, 200m resolution, nodata -9999.0 |
| **GeoJSON** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-geojson.json` | ✅ Verified | 80 Polygon features with cell inundation metrics, EPSG:32643 |
| **CSV** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-csv.csv` | ✅ Verified | Full 217-frame $\times$ 80-cell time series (depth, velocity, elevation) |
| **Shapefile** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-shapefile.zip` | ✅ Verified | Complete ESRI Shapefile package (.shp, .shx, .dbf, .prj) |
| **KML** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-kml.kml` | ✅ Verified | WGS84 geographic coordinates for Google Earth |
| **HTML Report** | `.../exports/a8bacdd4-490c-4961-a8c1-a3a2d4e3874b-html.html` | ✅ Verified | Interactive Leaflet visualization with depth symbology |

---

## 7. Next Steps for Historical Site Validation

To promote DamSafe from `UJJANI_APPROXIMATE_DEMONSTRATION` to `UJJANI_HISTORICAL_SITE_SIMULATION`, the remaining physical data gaps must be resolved:
1. Direct bathymetric soundings of the Bhima River bed.
2. High-frequency SCADA spillway telemetry.
3. Empirically calibrated stage-discharge rating curve at Pandharpur.
4. Field calibration of Manning's $n$ against surveyed high-water marks.
5. Survey geodetic tie for staff gauge datum to EGM96.

Detailed hydraulic audit findings, numerical scheme parameters, and resolution sensitivity analysis are documented in [UJJANI_HYDRAULIC_DIAGNOSTICS.md](file:///c:/Users/kunal/OneDrive/Desktop/DAM/docs/UJJANI_HYDRAULIC_DIAGNOSTICS.md).
