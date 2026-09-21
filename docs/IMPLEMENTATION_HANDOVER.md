# September 21 implementation handover

## Latest verification and delivery

- Full backend suite: **113 passed, 2 expected failures, 159 warnings** in 56.30 s. The expected failures are the two incomplete custom-site lifecycle integrations, not passes.
- Ruff: all checks passed. Production frontend build and Compose configuration passed. Vite still reports large JavaScript chunks.
- Real browser/API check: all nine pages; non-placeholder dashboard numbers; frame-40 fetch across a batch boundary; depth/velocity switching; native river 3D mesh; SPH frame-100 seek and playback; 80 native Ujjani polygons; all six exports.
- Fresh direct native D-Flow terrain/release and breach smoke tests ran with locally available DEMs and Docker image. SPH browser output is retained laboratory solver evidence.
- Added .env creation/loading, pinned Earth Engine and dotenv dependencies, service-account/OAuth initialization and redacted credential failures. Live Earth Engine remains unverified.
- Updated AGENTS.md. Removed empty kunal.md and duplicate DATASETS.md / FINAL_SCIENTIFIC_READINESS.md reports with unsupported readiness claims; retained contracts, source manifests and historical evidence.
- Replaced equal-area river columns with native face surfaces; fixed SPH camera, particle size, cancellation/cache/playback; added white/orange design, real first-frame dashboard values, project and result selectors, numerical comparison cards.
- Removed silent geospatial shim injection and filename-only satellite authenticity. Native rasterio/pyproj are required.
- Changes are prepared on local branch `latest` for the user-authorized commit. No push or publication is authorized.

The sections below record the earlier September 19 work; the verification above supersedes their test totals.

## Live startup follow-up

Started the documented SQLite preview on loopback port 8000. Fixed a navigation race in `frontend/src/main.tsx`: an asynchronous Results response no longer changes the page after the user navigates elsewhere. Production build passes; browser verification checks all nine pages and delayed-response navigation. Engine availability remains dependent on Docker/images; retained results are available without executing a new solver.

## Delivered

Orange/brown navigation, orange primary actions, accessible focus styling, print styles; valid breach snapshot saves; valid laboratory SPH spacing presets; selected hydrograph included in snapshot; resilient legacy scenario/status rendering; per-project result isolation; bounded field-aware playback; load-safe geographic map; native D-Flow mesh polygons with centre-identity verification; selected-frame area; report/run identity check; removal of fixed exposure totals; honest satellite-assessment blocking; ownership checks and SPH path validation.

## Changed files

- `backend/damsafe/api.py`: native geometry response and assessment/ownership guards.
- `backend/damsafe/numerics/geometry.py`: native polygon reader.
- `backend/damsafe/numerics/service.py`: reject custom site runs that would ignore the scenario.
- `backend/damsafe/numerics/sph_adapter.py`: validate run IDs.
- `backend/damsafe/observation/exposure.py`: unavailable instead of invented impact.
- `backend/tests/test_native_geometry.py`, `test_site_submission_guard.py`, `test_observation_phase4.py`, `test_phase4_e2e_lineage.py`: regression checks and corrected expectations.
- `frontend/src/main.tsx`, `types.ts`, `style.css`: playback/state/theme.
- `frontend/src/components/FloodMap2D.tsx`, `StatusBadge.tsx`: geometry/load/legacy handling.
- `frontend/src/pages/Dashboard.tsx`, `ScenarioBuilder.tsx`, `Results.tsx`, `ReportsExport.tsx`: workflow and honest semantics.
- `frontend/tests/review-local.mjs`: actual local API/browser review with screenshots and six exports.
- `docs/PROJECT_STATUS.md`, this handover: current status.

## Verification

- `python -m pytest -q --disable-warnings`: **109 passed, 4 skipped**, 152 warnings. Skips require Docker/native runtime prerequisites. No new native solver execution claimed.
- `npm run build`: PASS; large-bundle warning remains.
- `node tests/review-local.mjs` from `frontend/`: all nine pages PASS, no uncaught browser errors; actual retained Ujjani output contains 80 native polygons; GeoJSON, Shapefile, KML, GeoTIFF, CSV, HTML downloads PASS.
- `docker compose config --quiet`: PASS.
- Scoped `git diff --check`: PASS.
- Screenshots: `.local/ui-review/{dashboard,study-area,data-setup,scenario-builder,simulation,results,validation,impact,reports}.png`.

## Start

From repository root in PowerShell: `./scripts/start.ps1 -Preview`. Open `http://127.0.0.1:8000`. The retained Ujjani demonstration is selected when present; choose Simulation/Results to explore saved output. Engine execution still needs installed pinned images.

## Exact remaining work

This is a repaired demonstration, not a finished scientific system. Full saved-scenario binding to the site worker, Cesium terrain, qualified live SAR processing/assessment, genuine exposure/loss logic, full reach SPH and natural blockage modelling remain incomplete. Custom site submission explicitly returns 422 because the old worker ignored scenario fields. Retained results and laboratory runs remain supported.

External inputs still required: surveyed channel/structures, sourced reservoir and boundary/release records, spatial roughness, independent gauge data, authentic compatible satellite observations/credentials, licensed asset layers, and expert review. Existing outputs are retained real solver demonstrations; automated numerical fixtures are synthetic. Engineering gaps remain explicitly listed in PROJECT_STATUS.md.
