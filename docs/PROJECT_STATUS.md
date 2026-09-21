# DamSafe Project Status

**Assessment date:** 2026-09-21
**Overall:** application demonstration is available; Ujjani scientific assessment and operational deployment are not complete.

## September 21 implementation update

White/orange navigation now matches the supplied visual direction. The dashboard reads actual first-frame depth/area; project and run selectors are available. The map fits native mesh geometry and uses fixed numeric legends. River 3D now renders native face surfaces instead of equal-area columns. SPH uses bounds-fitted, Z-up orbit controls, pixel-sized particles, abortable requests and a bounded 12-frame cache. Browser checks exercise frame 40, field switching, both 3D canvases and SPH seek/playback.

Root .env is created locally and ignored by Git. Backend processes load it without overriding process settings. OAuth and service-account Earth Engine initialization are wired and unit-tested; live credentials/execution remain unverified. See [environment setup](ENVIRONMENT.md). A local SAR filename no longer establishes authentic provenance. Native rasterio/pyproj are required; silent approximation shims were removed.

Two legacy site lifecycle tests are explicitly expected failures because the worker cannot bind arbitrary saved site scenarios. They are not passes. Direct terrain/release and breach D-Flow smoke execution tests do run when the local DEMs and pinned Docker image are available.

Orange workspace theme and accessible focus/primary-button styling are applied. Fixed invalid breach-save fields, unsupported SPH spacing, hydrograph snapshot inclusion, legacy scenario rendering, project-change result isolation, depth/velocity frame mixing, map-load races, and selected-frame area display. Playback uses bounded 32-frame batches and waits for loaded frames.

The result window now attaches original D-Flow face boundaries when their centres match the normalized cells; the map renders those polygons. Centre-only fallback remains for runs lacking compatible native geometry. The retained Ujjani result returned 80 native face polygons. This is rendering the original computational mesh, not deriving a surveyed floodplain.

Hard-coded settlement/farmland values were removed. Satellite comparison now returns NOT_VALIDATED rather than comparing an event-maximum product to a falsely assigned acquisition time. Gauge/exposure and project-prefixed SPH endpoints check run ownership; SPH run-directory lookup rejects invalid IDs. Cesium remains unimplemented and the UI no longer claims a token enables it.

Checks: production build passed; backend checks and the nine-page browser review pass. The browser check reads 80 native Ujjani polygons and downloads all six real export formats. Native engines were not rerun. Browser review/screenshot command: `cd frontend` then `node tests/review-local.mjs`. Images are stored outside Git at `.local/ui-review/`.

Custom SITE_SCENARIO submission has been unblocked through a generic SiteConfiguration schema and generic scenario-to-solver case builder (`build_site_case`). Submission validates spatial CRS, river centerline, bounds, and snapshot integrity, computing deterministic configuration hashes. The worker binds the immutable scenario snapshot and executes real D-Flow FM solver containers, generating verified `normalized.nc` and `products.nc`. All 120 backend/evidence tests pass.

Remaining engineering work includes Phase 2 (River Blockage / Landslide Dam scenario mode and DualSPHysics coupling), Cesium 3D terrain, qualified historical SAR assessment, real asset-overlay/loss logic, and external surveyed hydraulic observations.

## Feature matrix

| Feature | Status | Evidence | Current meaning |
|---|---|---|---|
| Project/dataset/scenario persistence | IMPLEMENTED | contracts, migrations, foundation tests | immutable versioned inputs/snapshots |
| Readiness audits | IMPLEMENTED | readiness code/API/worker/tests | reports input gaps; does not run hydraulics |
| D-Flow FM benchmark execution | IMPLEMENTED | `docs/evidence/phase2`, pinned engine provenance | genuine saved solver evidence |
| DualSPHysics benchmark execution | IMPLEMENTED | `docs/evidence/phase2`, SPH parser/view API | genuine laboratory-scale evidence |
| Bounded Ujjani D-Flow demonstration | PARTIAL | phase5d/phase5e manifests/logs and retained local run | terrain/approximation-based scenario, not calibrated/validated |
| Breach formulation/sensitivity | PARTIAL | `site/breach.py`, phase5e evidence/tests | empirical scenario generator; not fully exposed end to end in API/UI |
| Normalized results/products | IMPLEMENTED | numerical result/product code and tests | depth/velocity/arrival/duration/states/area |
| 2D geographic result UI | IMPLEMENTED | `FloodMap2D.tsx`, result API | native mesh polygons when available; centres otherwise |
| SPH 3D UI | IMPLEMENTED | `Sph3DViewer.tsx`, SPH endpoints/tests | real retained particles; lab/near-field only |
| Regional 3D terrain | PARTIAL | `River3DViewer.tsx` | native face bed/water surfaces; surrounding terrain/Cesium absent |
| Run comparison | IMPLEMENTED | comparison module/API/tests | compatible numerical agreement, not accuracy |
| GIS/report exports | IMPLEMENTED | exporter/create/verify endpoints/tests | six formats; vectors are cell points |
| Earth Engine/Sentinel-1 path | PARTIAL | observation modules/tests | configurable query/import; live EE execution unverified here |
| Historical satellite assessment | BLOCKED | validation plan/readiness docs | no qualified matching event pair |
| Gauge validation | BLOCKED | gauge evaluator/API | insufficient independent records |
| Exposure/HADR | BLOCKED | `observation/exposure.py` inspection | no fabricated totals; qualified asset overlay remains unavailable |
| Loss/population/evacuation | DEFERRED | UI blocked states | required data/methods absent |
| Public multi-user deployment | BLOCKED | API security inspection | no authentication/authorization |

## Readiness

Dataset readiness is PARTIAL. Terrain files and source/manifests exist locally, but qualified bathymetry, structures, spatial roughness, time-aligned release/boundary/gauge observations, and exposure inventories remain absent or unverified. Exact site constants in code need primary-source review before being called verified.

Engine readiness is environment-dependent. Retained evidence proves both pinned engines executed benchmark cases. A local machine without the images reports them unavailable and skips native tests. DualSPHysics evidence does not represent 115 km regional modelling.

Frontend has nine workflow pages, connected APIs, a geographic map and SPH viewer. Backend supports persistence, workers, products, comparison and exports. Scientific-facing pages correctly need stronger gating around exposure and observation claims.

## PS deliverables

| Deliverable | Status |
|---|---|
| Generalized scenario framework with SPH and D-Flow FM | PARTIAL: both engines integrated; blockage/rainfall-runoff/full-domain SPH deferred |
| Customized input/scenario/output tool | IMPLEMENTED for current contracts; breach UI integration partial |
| Dashboard, large-data strategy and SHP/KML output | PARTIAL: dashboard/exports work; scale is bounded, not load-tested at operational volume |
| Near-real-time Earth Engine analysis | PARTIAL/BLOCKED live: configurable path; no verified live execution/coverage guarantee |
| Indian river/dam demonstration | PARTIAL: bounded Ujjani demonstration exists, not scientifically validated |

## What is demonstrable today?

- Start a local preview, inspect Ujjani project/readiness and create immutable input/scenario records.
- Reopen genuine retained D-Flow FM and DualSPHysics benchmark output.
- Reopen the bounded Ujjani approximate D-Flow result where local artifacts/database are present.
- Animate saved 2D fields, view real saved SPH particles, compare compatible runs, and generate/verify six export formats.
- Demonstrate honest DATA REQUIRED/BLOCKED states for unavailable scientific evidence.

## What must not be claimed yet?

- An operational forecast, official warning, calibrated Ujjani flood model or independently validated breach prediction.
- Live near-real-time Earth Engine operation or daily coverage.
- Real Ujjani affected population, settlements, farmland, roads, facilities, monetary loss, risk zones or evacuation routes.
- Real-world “accuracy” from SPH/D-Flow agreement or satellite comparison of an unrelated event.
- True 3D regional hydrodynamics, Cesium terrain, or full-domain SPH.
- Full PS compliance or production/public security.

## Blockers and technical debt

High-priority external inputs: surveyed bathymetry/cross-sections, dam/structure primary sources, calibrated release/rating data, initial/downstream/tributary series, spatial roughness, independent gauges, authentic compatible Sentinel-1 products/live EE access, and licensed exposure layers. Domain-expert review is absent.

High-priority engineering tasks: integrate breach/release inputs through the immutable site-worker flow; finish Earth Engine raster processing and compatible historical assessment; implement qualified asset overlays; add authentication before public deployment; improve retained-result redistribution and full-domain performance evidence. Old phase reports are historical records, not current readiness claims.
