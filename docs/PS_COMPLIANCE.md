# PS 26161 Phase 5B.2 implementation note

Phase 5B.2 establishes genuine hydrodynamic wave propagation and 2D spatial rasterization for the Ujjani–Bhima reach on branch `feature/phase-5b-ujjani-hydraulic-run`.

The dynamic run (`run_id`: `a8bacdd4-490c-4961-a8c1-a3a2d4e3874b`, `project_id`: `ujjani-persistent-proj-001`, `scenario_id`: `ujjani-persistent-scen-002`) resolved boundary decoupling and standing backwater via `ExtForceFileNew`, polyline node snapping, and sloping initial water levels (`ujjani_init.ext`).

Dynamic velocities (up to 7.55 m/s), wave celerity (~38.3 km/h), mass balance residual (-102.0 m³, 0.000004% relative error), and true 2D GeoTIFF rasterization ($111 \times 216$ cells, 200m res) were achieved and verified. All 6 export formats were generated and independently reopened. Retained Phase 5B.1 run `a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a` for regression comparison. Model classification remains strictly `UJJANI_APPROXIMATE_DEMONSTRATION`.

| Deliverable | Status | Code / evidence | Missing completion evidence |
| --- | --- | --- | --- |
| Dynamic boundary coupling | tested | `hydraulic_case.py` (`ExtForceFileNew`, dynamic `.pli`), `test_phase5b2_hydraulic_dynamics.py` | Live SCADA boundary streaming |
| Sloping initial water surface | tested | `hydraulic_case.py` (`ujjani_init.ext` + `initial_water_level.xyz`) | Measured dry-season water surface survey |
| Mass conservation verification | tested | `diagnostics.py` (0.000004% mass error) | Multi-tributary lateral balance |
| 2D spatial GeoTIFF rasterization | tested | `exports.py` (200m grid, $111 \times 216$ cells) | LiDAR fine-grid rasterization |
| Independent export verification | tested | `test_phase5b2_hydraulic_dynamics.py` (all 6 formats) | Production cartographic map series |

# PS 26161 Phase 5B.1 implementation note

Phase 5B.1 turns the successful approximate Ujjani D-Flow FM execution into a persistent, reproducible DamSafe run with complete provenance, normalization, derived products, independently reopened GIS exports, and restart persistence on branch `feature/phase-5b-ujjani-hydraulic-run`.

The persistent run (`run_id`: `a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a`, `project_id`: `ujjani-persistent-proj-001`, `scenario_id`: `ujjani-persistent-scen-001`) was submitted through `run_service.submit_run()`, processed by `run_worker.process_next_job()` through states `QUEUED` → `RUNNING` → `SUCCEEDED`, and saved to `.local/runs/a7a2c6cf-2335-4e1d-b395-ae7ec4e4d57a/`.

Normalized results (`normalized.nc`), products (`products.nc`), and 6 export formats (GeoTIFF, GeoJSON, CSV, Shapefile, KML, HTML) were generated and verified. Restart persistence was proven across isolated database connections. The run is strictly classified as `UJJANI_APPROXIMATE_DEMONSTRATION`.

| Deliverable | Status | Code / evidence | Missing completion evidence |
| --- | --- | --- | --- |
| Persistent site run lifecycle | tested | `backend/damsafe/numerics/service.py`, `worker.py`, `test_phase5b1_persistent_run.py` | Full multi-worker production queue |
| Ujjani NetCDF normalization | tested | `backend/damsafe/numerics/results.py`, `normalized.nc` (217 frames, 80 cells) | Verified 3D bathymetry |
| Site postprocessing & products | tested | `backend/damsafe/numerics/products.py`, `products.nc` (depth, arrival, duration) | Field high-water calibration |
| Reopened site GIS exports | tested | `backend/damsafe/exports.py`, all 6 formats verified | Production cartographic styling |
| Restart persistence verification | tested | `test_phase5b1_persistent_run.py` (engine re-instantiation) | Multi-node cluster failover |

# PS 26161 Phase 5A implementation note

Phase 5A adds Ujjani site data acquisition and model-readiness assessment. The site specification module (`backend/damsafe/site/ujjani.py`) codifies authoritative dam parameters from CWC/WRD sources. Preprocessing utilities (`backend/damsafe/site/preprocessing.py`) provide traceable unit conversion (cusecs ↔ m³/s), timezone alignment (IST → UTC), and coordinate projection (WGS84 ↔ UTM Zone 43N). The 16-item readiness gate (`backend/damsafe/site/readiness_gate.py`) formally evaluates site simulation prerequisites and returns `NOT_READY_FOR_SITE_RUN` due to missing sub-surface bathymetry, continuous forcing telemetry, and downstream rating curve.

Historical events are selected (October 2020 primary, August 2019 secondary) with matched Sentinel-1 GRD scene pairs. No site simulation is executed or claimed. The `TERRAIN_APPROXIMATION_ONLY` classification prevents terrain-only channel approximations from being labelled as verified bathymetry.

| Deliverable | Status | Code / evidence | Missing completion evidence |
| --- | --- | --- | --- |
| Ujjani dam/reservoir specification | tested | `backend/damsafe/site/ujjani.py`, `test_phase5a_site_readiness.py` | Independent survey verification |
| Discharge/timezone/CRS preprocessing | tested | `backend/damsafe/site/preprocessing.py`, round-trip tests | Production continuous telemetry stream |
| 16-item model-readiness gate | tested | `backend/damsafe/site/readiness_gate.py`, 16-item evaluation test | BLOCKED items require government data releases |
| Historical event selection & SAR matching | documented | `docs/UJJANI_EVENT_MANIFEST.md` | Live GEE processing of authentic scenes |
| Site data catalogue | documented | `docs/UJJANI_SITE_DATA.md` | Field-verified bathymetry and rating curves |
| Model readiness matrix | documented | `docs/UJJANI_MODEL_READINESS.md` | Progression from NOT_READY to READY requires 3 blocked items resolved |

# PS 26161 Phase 3C implementation note

The Phase 3B UI consumes only existing run-scoped Phase 3A contracts. It does not turn synthetic laboratory output into a Ujjani claim. The result viewer distinguishes saved numerical values from visual presentation, retains wet/dry/nodata states, uses fixed comparison semantics, and exposes provenance in a technical details panel. Exposure and economic damage are explicitly unavailable because verified producer/year/coverage/aggregation metadata, asset inventories, values and vulnerability functions are absent. Export actions are disabled until verified processing outputs exist.

Phase 3C now provides immutable ensemble submissions, scenario-frequency summaries (never probabilities), exact cache identity through the existing run service, and independently reopenable GeoTIFF/KML/GeoJSON/Shapefile/CSV/HTML exports. Export filenames and paths are sanitized; Shapefile field truncation is documented in each archive. No export is created when the saved result lacks a usable CRS. Settlement exposure, response priorities and economic damage remain unavailable without verified datasets and vulnerability inputs.

Remaining gaps are recorded below and must not be hidden with placeholder metrics.

# PS 26161 deliverable evidence matrix

This maps the supplied implementation brief's interpretation of PS 26161. The original official PS and the full PRD were not present. Status uses implemented/tested/blocked/deferred; a blocked row may have preparatory code but is not a completed deliverable.

| Deliverable | Status | Code / evidence | Missing completion evidence |
| --- | --- | --- | --- |
| Reusable input contracts / provenance | tested | `contracts.py`, `ingestion.py`, `storage.py`; software tests | Broader data/provider formats; production S3 verification |
| Real Ujjani data audit | tested | Raw NWIC downloads; `evidence/*audit.json` | Physical pathway, timezone and event suitability unresolved |
| Project/scenario/dataset API | tested | `api.py`, SQLAlchemy persistence and snapshot tests | PostgreSQL runtime verification |
| Input-readiness interface | tested | React/TypeScript setup UI and backend checks | Hydraulic interpretation review and derived-domain setup |
| PostgreSQL/PostGIS service and migrations | tested locally | Docker Compose PostGIS 16/3.5, migration and `PostGIS_Version()` query | Production deployment and concurrent load not assessed |
| Background queue | tested locally | SQL audit and numerical workers; bounded/cancellable execution, stale-lease recovery tests | Production worker supervision and load limits still require review |
| Immutable hydraulic run manifest contract | tested locally | `runs` table, input update/delete trigger, idempotent API, execution/result separation | Imported-output workflow and production concurrency not implemented |
| D-Flow FM actual execution | tested locally | Pinned runtime image, exact official f34 case, lake-at-rest and shared native runs; `PHASE2_EVIDENCE.md` | Ujjani domain and forcing absent; local analytical check does not validate site |
| DualSPHysics actual execution | tested locally | Real CPU image, original official 0.01 m run, 0.02 m automatic solver-to-normalized run; `PHASE2_EVIDENCE.md` | Mass loss and literature-reference interpretation prevent validation claim |
| Computed breach/reservoir routing | blocked | Separate typed contract and analytical prescribed-pathway storage balance | Verified component/method, level–storage and all physical release inputs |
| Compatible SPH/D-Flow benchmark comparison | tested locally | Physically matched synthetic closed-tank case, depth/extent/runtime agreement report | Breaking/impact interpretation and SPH mass loss limit validation; no site comparison |
| Compatible Ujjani site comparison | blocked | One-site scope retained | Verified site inputs and two genuine local runs |
| Depth/velocity normalization | tested locally for both engines | Genuine SPH PartVTK and D-Flow face-centred map outputs to NetCDF | Ujjani mesh/forcing absent; SPH local impact zones require interpretation |
| Saved-result products and bounded API | tested locally for synthetic solver output | `numerics/products.py`, run-scoped API and [Phase 3A report](PHASE3A_REPORT.md); genuine D-Flow saved-output integration test | No Ujjani run, verified permanent-water mask or site product |
| Ujjani arrival/duration outputs | blocked | General saved-output derivation exists; no site result exists | Verified site inputs and an actual site-specific run |
| Exposure assessment | blocked | Vector import only | Verified layers and hydraulic results, phase 3 |
| Economic losses | blocked | Deliberately unavailable | Asset values and applicable vulnerability functions |
| GeoTIFF/KML/GeoJSON/Shapefile/CSV/report exports | tested locally | `exports.py`, run-scoped download/verification endpoints, independent raster/vector/archive reopening tests | Production CRS/domain validation, PDF renderer and site-specific geospatial results |
| Google Earth Engine near-real-time path | tested locally / unverified live | `gee.py`, `import_fallback.py`, Sentinel-1 GRD pipeline, fallback import verified | GEE account credentials unavailable in offline test environment |
| Historical event assessment | tested locally | `comparison.py`, confusion matrix, IoU, Precision, Recall, F1 metrics | Verified site hydraulic forcing hydrograph |
| Exposure assessment | tested locally | `exposure.py`, settlement & farmland spatial overlay | Verified population raster and critical infrastructure layers |
| Economic losses | blocked | `exposure.py`, explicitly BLOCKED | Asset values and applicable vulnerability functions |
| Uncertainty ensemble / response priorities | implemented / partially blocked | Immutable ensemble API, genuine variant run submissions, exact configuration hashes and saved-output extent/depth/arrival ranges; response priorities explicitly unavailable | Verified Ujjani site variants, exposure datasets and scenario-consistent settlement explanations |
| Local demonstration | implemented | `scripts/start.ps1`, Phase 4 modelling UI | Final readiness documented in `FINAL_READINESS.md` |
| Natural river blockage / erosion / debris | deferred | Explicit supplied scope | Separate modelling work |
| Rainfall-runoff generation | deferred | Prescribed/derived release scope | Separate hydrological model |
| Full-river 3D SPH / two-way coupling | deferred | Local comparison interpretation | Confirm spatial comparison expectation with sponsor |

There is no full PS compliance claim. Imported authentic numerical outputs, if added later, must have origin/engine/parameters/input hashes and cannot prove automatic execution. No synthetic flood layer or sample rupee loss is used to fill these gaps.
