# Verification and scientific validation plan

## Phase 5A site data readiness assessment

Phase 5A adds a formal 16-item Ujjani model-readiness gate ([UJJANI_MODEL_READINESS.md](UJJANI_MODEL_READINESS.md)) that must evaluate all physical inputs before any site simulation is permitted. The current verdict is `NOT_READY_FOR_SITE_RUN` with 3 BLOCKED items.

**Validated inputs (PASS):** Copernicus GLO-30 terrain (30 m), HydroRIVERS reach geometry (115 km), CWC/WRD dam specification (crest 497.0 m, 41 gates), storage capacity (3.14 km³ gross), EPSG:32643 CRS, IST→UTC temporal alignment, JRC permanent water baseline.

**Partially validated (PARTIAL):** Gate discharge rating curves (dimensions known, head-discharge relationship unknown), forcing attribution (raw NWIC gate data, pathway mapping incomplete), roughness (literature Manning's n, uncalibrated), vertical datum (EGM96, local gauge zero unverified), October 2020 event selection (peak known, continuous hydrograph unavailable), Sentinel-1 scene pair (IDs matched, not processed).

**Blocked:** Sub-surface channel bathymetry (requires WRD/CWPRS survey), continuous upstream forcing telemetry (requires SCADA access), Pandharpur downstream rating curve (requires CWC release).

**Site validation prerequisites (must be met before claiming site-validated simulation):**
1. All 3 BLOCKED items resolved to at least PARTIAL.
2. At least one complete Ujjani site hydraulic simulation executed with verified forcing.
3. Authentic Sentinel-1 SAR flood extent processed via GEE or fallback import.
4. Simulation output compared against authentic satellite observation at compatible acquisition time on valid shared spatial grid.
5. Flood agreement metrics (IoU, Precision, Recall, F1) computed and reported with uncertainty bounds.
6. Roughness coefficient calibrated against observed flood extent for at least one historical event.

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
