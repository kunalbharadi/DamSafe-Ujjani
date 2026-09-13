# Verification and scientific validation plan

## Phase 5B.2 Genuine Ujjani Hydraulic Dynamics & Flood-Wave Demonstration

Phase 5B.2 transitions DamSafe to genuine hydrodynamic wave propagation along the 115 km Ujjani–Bhima reach with active wave celerity, mass balance verification, and 2D spatial rasterization:
- **Persistent Run Identity:** `run_id`: `a8bacdd4-490c-4961-a8c1-a3a2d4e3874b`, `project_id`: `ujjani-persistent-proj-001`, `scenario_id`: `ujjani-persistent-scen-002`.
- **Dynamic Wave Characteristics:** Upstream peak depth 6.44m (velocity 7.55 m/s) at $t=72\text{ h}$; Mid-reach peak depth 8.51m (velocity 2.67 m/s) at $t=74\text{ h}$; Pandharpur peak depth 8.57m (velocity 2.80 m/s) at $t=75\text{ h}$.
- **Mass Balance:** Inflow $2.344\times 10^9\text{ m}^3$, Outflow $2.342\times 10^9\text{ m}^3$, Storage change $2.202\times 10^6\text{ m}^3$, Residual $-102.0\text{ m}^3$ (relative error $0.000004\%$).
- **Spatial Products:** 2D GeoTIFF rasterization ($111 \times 216$ cells, 200m res) in EPSG:32643, all 6 GIS formats independently reopened and verified.
- **Classification:** `UJJANI_APPROXIMATE_DEMONSTRATION` (retains Phase 5B.1 run `a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a` for regression comparison).
- **Diagnostics & Run Reports:** [UJJANI_HYDRAULIC_DIAGNOSTICS.md](UJJANI_HYDRAULIC_DIAGNOSTICS.md), [UJJANI_FIRST_RUN_REPORT.md](UJJANI_FIRST_RUN_REPORT.md).

## Phase 5B.1 Persistent Ujjani Hydraulic Run, Normalization & Export

Phase 5B.1 transitions DamSafe from `NOT_READY_FOR_SITE_RUN` to `READY_FOR_APPROXIMATE_SITE_RUN` and executes the first persistent, fully normalized, postprocessed, and exported 2D hydrodynamic simulation for the Ujjani–Bhima reach using the Deltares D-Flow FM solver through the standard DamSafe run service lifecycle.

- **Persistent Run Identity:** `run_id`: `a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a`, `project_id`: `ujjani-persistent-proj-001`, `scenario_id`: `ujjani-persistent-scen-001`.
- **Case Configuration:** 115 km reach from Ujjani Dam to Pandharpur in `EPSG:32643` (UTM Zone 43N), 80 quadrilateral cells.
- **Forcing:** Digitized October 2020 flood release hydrograph (peak ~250,000 cusecs / 7,079.2 m³/s).
- **Execution Lifecycle:** Standard `run_service` / `run_worker` (`QUEUED` → `RUNNING` → `SUCCEEDED`), runtime ~10.1s, 217 output timesteps across 777,600 s (9 days).
- **Numerical Quality:** Zero NaN, Inf, or negative water depths (depth range: [6.50 – 54.25] m). Water balance error: 0.0006 m³.
- **Postprocessing & Exports:** Normalized NetCDF (`normalized.nc`), products NetCDF (`products.nc`), and 6 verified GIS exports (GeoTIFF, GeoJSON, CSV, Shapefile, KML, HTML).
- **Restart Persistence:** Verified state recovery by reconnecting with a fresh database engine instance.
- **Classification:** `UJJANI_APPROXIMATE_DEMONSTRATION` (honest approximate demonstration; not certified as historical simulation).
- **Detailed Run Report:** [UJJANI_FIRST_RUN_REPORT.md](UJJANI_FIRST_RUN_REPORT.md).

## Phase 5A site data readiness assessment

Phase 5A adds a formal 16-item Ujjani model-readiness gate ([UJJANI_MODEL_READINESS.md](UJJANI_MODEL_READINESS.md)) that evaluates all physical inputs. In strict mode without approximations, verdict is `NOT_READY_FOR_SITE_RUN`.

**Validated inputs (PASS):** Copernicus GLO-30 terrain (30 m), HydroRIVERS reach geometry (115 km), CWC/WRD dam specification (crest 497.0 m, 41 gates), storage capacity (3.14 km³ gross), EPSG:32643 CRS, IST→UTC temporal alignment, JRC permanent water baseline, October 2020 event definition, Sentinel-1 scene pair matching.

**Partially validated (PARTIAL):** Channel bathymetry (`TERRAIN_ONLY_CHANNEL_APPROXIMATION`), gate discharge rating curves, upstream initial state, forcing hydrograph (digitized), downstream boundary (normal depth), roughness (literature Manning's n), vertical datum (EGM96).

**Site validation prerequisites (must be met before claiming historical site-validated simulation):**
1. Sub-surface riverbed soundings/cross-sections below water level obtained.
2. Continuous hourly SCADA discharge telemetry obtained.
3. Pandharpur stage-discharge rating curve calibrated.
4. Manning roughness calibrated against surveyed flood high-water marks.
5. Surveyed datum tie between local gauge zero and EGM96 geoid.

Phase 2 execution status is in [PHASE2_EVIDENCE.md](PHASE2_EVIDENCE.md). Both genuine engines have executed official examples and a shared synthetic benchmark; the original DualSPHysics example was normalized afterward following a parser fix, while a 0.02 m variant completed automatically. D-Flow FM passed a separate lake-at-rest analytical check. The bundled SPH literature front-position check has measured errors, but native particle mass loss and reference-convention uncertainty preclude a validation badge. No Ujjani site run or site comparison is claimed. The existing gates below remain acceptance criteria, not claims of completion.

Software tests cannot validate Ujjani hydraulics. Phase 1 tests concern input handling, traceability, separation of projects and persistence. Synthetic files exist exclusively in temporary test projects.

## Executed phase 1 checks

`backend/tests/test_foundation.py` exercises gaps, missing values, duplicate times and flags without interpolation; explicit cusec conversion and timezone rejection; unsafe filenames and malformed/oversized uploads; separate synthetic project enforcement; immutable version/snapshot hashes and database triggers; reopening the database with a new application instance; cross-project scenario denial; CRS mismatch, nodata and unknown datum; physically distinct forcing contracts; monotonic storage-curve checks; durable audit execution/cancellation; vector geometry and safe storage paths.

The TypeScript production build and frontend dependency audit are run independently. Browser smoke checks use `frontend/tests/setup.spec.ts` against a running local server, including page navigation, empty/readiness states, mobile width and console errors. They do not prove the Phase 3A solver-backed result API or the future Prompt 3B result viewer.

PostgreSQL/PostGIS runtime, PostgreSQL immutability/concurrency, Docker image builds and real S3 operations require their services and are not covered by SQLite tests. Do not mark these as passing through a skip.

## Phase 2 execution gates

1. Establish native engine identity, version/source commit, executable hashes and supported command invocation from official documentation. Run the official small example, preserving input, logs, output, time and hardware.
2. Reproduce an independent analytical or laboratory benchmark appropriate to each engine. The DualSPHysics official `01_DamBreak` directory includes a validation case and attributed Koshizuka/Oka dam-tip reference data; inspect original provenance and permitted redistribution before packaging it.
3. Check storage and all inflow/outflow pathways; ensure nonfinite/negative state detection, wet/dry consistency and suitable model tolerances. Inspect stability and grid/time/particle sensitivity.
4. Prepare a common physical domain, initial state, forcing, gauges and output times. Document SPH-to-depth-averaged observables; inter-model difference is agreement, not truth accuracy.
5. Use verified Ujjani inputs for a separate site run, then a compatible small local SPH/D-Flow comparison. A generic benchmark does not satisfy the site comparison.
6. Absent executable, nonzero exit, truncated/corrupt output, cancellation or timeout must never become SUCCEEDED. No simulation fallback or browser-generated flood.

## Later product and observation gates

Depth/velocity/arrival/duration must derive from stored solver output with masks, projection and threshold metadata. Validate exports by reopening them with an independent reader. Preserve not-reached and outside-domain separately. Exposure is not monetary damage or casualties.

Phase 3A executed software verification of the saved-result API, masks, arrival and duration products, cache/source identity and bounded reads. Its integration test directly reopens the retained genuine D-Flow shared synthetic normalized NetCDF and compares derived flooded area to the native saved frame; the local test run required that file to exist, so absence was not counted as a pass. See [Phase 3A report](PHASE3A_REPORT.md). Product correctness on this synthetic case is not hydraulic validation or evidence of a site flood. Verify future georeferenced baseline water masks, cross-datum handling, arrival precision against saved intervals, large-result load and Ujjani spatial outputs independently when actual site data are available.

Historical observation assessment requires the actual acquisition time, matching forcing and valid shared spatial mask, with documented empty-mask behaviour for IoU/precision/recall/F1. Do not compare event-maximum predicted extent with an instantaneous satellite image without a justified reference definition. Separate calibration from independent assessment. Hypothetical failure runs cannot inherit historical validation status.

No numeric accuracy targets, tolerances, runtime guarantees or validation scores are invented in phase 1. A hydraulic-domain expert review is outstanding.
