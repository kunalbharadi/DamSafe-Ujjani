# DamSafe — SIH Technical Q&A Guide

Answers to critical scientific, hydraulic, numerical, and operational questions for SIH judges.

---

### 1. Why use both D-Flow FM and DualSPHysics?
D-Flow FM is a 2D unstructured-grid shallow water equation (SWE) solver optimized for regional flood wave propagation over long distances. DualSPHysics is a 3D Smoothed Particle Hydrodynamics (SPH) solver designed for near-field, highly turbulent, free-surface dam breach hydrodynamics. Combining them allows near-field 3D splash/impact modeling coupled with regional downstream inundation mapping.

### 2. Why not use HEC-RAS exclusively?
HEC-RAS 2D is a SWE solver, but it cannot capture 3D non-hydrostatic fluid motion, vertical accelerations, or violent impact forces against dam walls during catastrophic collapse, which DualSPHysics handles natively.

### 3. Is this currently a validated Ujjani Dam simulation?
No. DamSafe explicitly reports that no validated Ujjani site simulation currently exists because sub-surface riverbed bathymetry, structure rating curves, and zero-gauge datum alignments are not yet verified against on-site measurements.

### 4. Where did your terrain data come from?
Terrain is imported from SRTM 30m / DEM Copernicus datasets.

### 5. How was river bathymetry handled?
Bathymetry below the water surface is currently uncalibrated due to lack of underwater cross-section surveys.

### 6. What is the vertical datum?
The terrain uses EGM96 orthometric height.

### 7. How is breach flow generated?
Breach hydrographs are derived from parametric breach equations (MacDonald-Langridge-Monopolis or Froehlich) or prescribed hydrograph inputs bound to scenario contracts.

### 8. How did you validate numerical results?
Numerical solvers were verified against standard analytical benchmarks (Ritter dam break, Stoker 1D, wet/dry boundary tests) and genuine retained synthetic NetCDF solver outputs.

### 9. Is Sentinel-1 satellite imagery absolute ground truth?
No. Sentinel-1 SAR flood maps contain classification uncertainties due to specular reflection on wet vegetation, radar shadow in hilly terrain, and speckle noise. Therefore, metrics are labeled "agreement with satellite-derived flood reference" rather than "ground truth accuracy".

### 10. Why use Google Earth Engine for Sentinel-1?
Earth Engine provides automated cloud-based ingestion, calibration, terrain flattening, and speckle filtering for Sentinel-1 Synthetic Aperture Radar (SAR) imagery without requiring local petabyte-scale storage.

### 11. Is satellite data available every day?
No. Sentinel-1 has a 6-to-12 day revisit cycle depending on orbit configuration over the Bhima basin.

### 12. How do you handle radar shadow and layover?
Terrain layover and shadow regions are masked using DEM slope and HAND (Height Above Nearest Drainage) thresholds, classified explicitly as `UNRELIABLE`.

### 13. How do you handle permanent water bodies?
Permanent water surfaces (such as the main Ujjani reservoir surface) are masked using the JRC Global Surface Water seasonality dataset so normal lake area is not counted as new flood extent.

### 14. What is IoU (Jaccard Index) and why use it?
Intersection over Union ($IoU = \frac{TP}{TP + FP + FN}$) measures spatial overlap between simulated and observed flood extents. It penalizes both over-prediction (FP) and under-prediction (FN) without being skewed by large dry land areas (TN).

### 15. Did you calibrate and validate on the same event?
No. Calibration parameters must always be evaluated on separate independent events. Using the same event for both invalidates scientific assessment.

### 16. Can a monsoonal river flood validate a dam-break scenario?
No. A natural monsoonal flood wave has lower peak velocity and longer duration than a violent dam-break breach wave.

### 17. What happens if there is no satellite image during a flood?
The system reports `UNAVAILABLE` or uses the authentic observation import fallback path when external airborne/satellite observations are uploaded.

### 18. What happens without an internet connection during judging?
DamSafe automatically uses its authentic offline observation fallback path and precomputed synthetic laboratory benchmarks without breaking.

### 19. Is SPH running in real-time on GPU?
DualSPHysics GPU solver runs near-field 3D SPH hydrodynamics. For full-domain regional scales, precomputed or 2D SWE solvers are used due to extreme particle count constraints.

### 20. Which results are cached?
Identical scenario run requests with matching SHA-256 hashes are served from verified result caches.

### 21. What does your ensemble mean?
Ensemble outputs represent scenario sensitivity across varying input parameters. Counts represent **scenario frequency**, not statistical probability.

### 22. Is scenario frequency equivalent to flood probability?
No. Scenario frequency indicates how many tested parameter combinations resulted in flooding at a specific cell; it is not a statistical return-period probability.

### 23. How do you calculate exposed population?
Exposed population is calculated by spatial overlay of flood depth with high-resolution population rasters. If population data is missing, DamSafe returns `UNAVAILABLE`.

### 24. Where do economic damage estimates come from?
Monetary damage requires verified asset valuation databases and depth-damage curves. If absent, DamSafe returns `LOSS_ESTIMATION = BLOCKED`.

### 25. How do you prevent false confidence?
By enforcing strict evidence states (`PASS`, `PARTIAL`, `BLOCKED`, `DEFERRED`, `UNVERIFIED`) and explicitly displaying missing data warnings in the UI.

### 26. Can hydraulic authorities reproduce your runs?
Yes. Every scenario and run is bound to immutable JSON contracts with SHA-256 hashes, deterministic solver parameters, and versioned datasets.

### 27. What is still incomplete?
On-site riverbed bathymetry, gauge zero-datum alignment, and live GEE cloud credentials.

### 28. What is required before operational deployment?
On-site acoustic Doppler current profiler (ADCP) river bathymetry surveys, calibrated spillway rating curves, and formal hydro-meteorological authority sign-off.

### 29. How does DamSafe handle multi-user security?
DamSafe enforces strict project storage isolation, path sanitization, a 64MB upload limit, and origin verification.
