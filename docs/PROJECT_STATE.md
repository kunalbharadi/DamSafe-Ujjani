# Project state — Prompt 2 partial completion

Date: 2026-09-13. Phase 2 has genuine, locally built D-Flow FM and DualSPHysics CPU engines. Both executed exact official examples and a physically matched synthetic closed-tank benchmark. D-Flow also passed a lake-at-rest analytical check; mesh/time-step variants and two SPH particle spacings have computed sensitivity differences. The original 0.01 m SPH example completed native stages and was normalized afterward following a parser fix; a 0.02 m variant completed solver-to-normalized processing automatically. See [Phase 2 evidence](PHASE2_EVIDENCE.md) for run IDs, hashes, runtime, comparison metrics and quality concerns.

The original phase 1 application remains working. PostgreSQL/PostGIS 16/3.5 was started and its migrations executed through Docker Compose; the explicit SQLite preview is still useful for running the host-installed numerical image. The phase 2 API persists bounded, cancellable numerical jobs for synthetic laboratory projects and rejects Ujjani site submissions with readiness findings. The UI has a separate numerical-runs page with engine capability status. The `prescribed_storage_balance` diagnostic is not a computed-breach model. Verified Ujjani bed/structures, total release Q(t), initial/downstream/tributary conditions, roughness, dam-component applicability and storage curve remain missing, so no Ujjani flood or comparison is claimed.

Software suite: 28 tests passed on 2026-09-13, including regression checks for D-Flow native-error and truncated-map false success. Frontend production build and browser smoke passed with the numerical-runs page at the previous checkpoint. A binary VTK parser reads genuine PartVTK `POLYDATA` and refuses corrupt topology/payload; the D-Flow NetCDF parser and water-balance diagnostics were exercised on native output. The original phase 1 state below is retained as historical handover, not as current status.

## Historical phase 1 handover

Date: 2026-09-12. Project root: `C:\Users\kunal\OneDrive\Desktop\DAM`.

**Current stage: Prompt 1 foundation implemented and locally tested; infrastructure and hydraulic-data prerequisites remain blocked. Prompts 2–4 have not been executed.** The supplied sequence explicitly calls for reviewing phase 1 data/engine evidence before expecting credible numerical outputs.

## Preserved inputs and scope

- Added the exact `DamSafe_Ujjani_Four_Codex_Prompts.md` from Downloads to this root.
- Preserved the initially empty `kunal.md`; no pre-existing application code or Git repository existed.
- Copied the supplied short implementation brief into `docs/SUPPLIED_BRIEF.txt`. The full PRD referenced inside it was not supplied. No full-PRD review or analysis of the previously mentioned guidelines PDF is claimed.
- No applicable AGENTS.md was found at the project or checked ancestor locations. No subagents, unrelated repositories, commits, pushes or public deployments were used.
- Ujjani is the demonstration site. No downstream endpoint, bathymetry, storage curve or settlement count has been invented.

## What runs

FastAPI/Pydantic API; React/TypeScript setup UI with MapLibre loaded only for a verified domain; immutable versioned raw-file uploads; hydrology/terrain/vector inspections; scenario snapshots; readiness checks; durable SQL background audit jobs and cancellation; Alembic migrations; local filesystem storage. An S3 upload/delete implementation and PostgreSQL/PostGIS Compose deployment exist but have not been exercised against those services.

The explicit Windows preview uses SQLite because Docker Desktop's Linux service is unavailable. This architecture is displayed in the UI and returned by `/api/health`. The default startup remains the proposed PostgreSQL/PostGIS Compose stack. No hydraulic output is mocked or generated; `/runs` returns 503 with an explanation.

## Verification evidence

- CPython 3.12.10, Node 24.19.0, npm 11.17.0. Python dependencies locked in `uv.lock`; frontend dependencies locked in `frontend/package-lock.json`.
- `python -m pytest -q`: 18 tests passed, including GeoPackage ingestion, actual streamed-size limits, time coverage and datum mismatch. See `docs/evidence/verification.txt` for output.
- `python -m ruff check backend scripts`: passed after formatting/corrections.
- `npm run build`: passed. MapLibre was upgraded to 6.9.0 after the dependency audit flagged older versions, and its named import API was corrected. The map library remains a large optional chunk; the setup screen loads separately.
- `npm audit`: zero known vulnerabilities in the checked frontend lockfile. This is a point-in-time dependency check, not a security certification.
- `docker compose config --quiet`: passed configuration validation. Docker runtime, image build and PostGIS execution did **not** run.
- `npx playwright test`: setup browser navigation, empty states, mobile width and console-error check passed in headless Microsoft Edge. Screenshots: `evidence/setup-desktop.png`, `evidence/setup-mobile.png`.
- Local Uvicorn bootstrap served `/`, assets, `/api/health`, projects, datasets, scenarios, readiness and jobs. The one-command preview startup was also invoked during final verification. Startup and remaining checks are recorded in `evidence/verification.txt`.

Dependency deprecation warnings from Starlette's httpx compatibility and Rasterio/Affine are recorded as warnings, not skipped tests or failures. No real solver test was marked passing.

## Actual Ujjani audit

Two actual NWIC resources were retrieved as CSV (4,026 and 1,411 rows) and preserved in ignored `data/raw/`. Their catalogue metadata, source checksums and per-gate records were audited; see DATA_MANIFEST and `evidence/hydrology-audit.json`. The raw CSVs are not imported into the application as certified total river outflow.

Critical unresolved inputs: source timezone; physical gate/pathway mapping and complete aggregate release; substantial time gaps; actual file units cusec versus catalogue m³/s; appropriate terrain and channel bed geometry with compatible elevation datum; domain/structure review; initial/downstream/tributary conditions; roughness. Computed breach additionally lacks verified component geometry, method applicability and level–storage/initial state/release pathways.

## Native engines and infrastructure

Neither solver was found on PATH or started. D-Flow FM's required native Windows development stack was absent at checked locations. DualSPHysics's inspected GitHub binaries contained supporting tools, not the main solver; the complete-package page requires a form/CAPTCHA and no submission was made. Source commits, exact checked prerequisites and candidate examples are in ENGINE_AUDIT.

Automatic approval review rejected one combined command containing Docker Desktop startup, reporting only “blocked by policy.” Independent file/network work continued. There was no user authorization request and no attempt to bypass the rejected startup. The SQLite preview is an explicit alternate deployment; PostgreSQL testing is still outstanding.

## Next stage entry point

Read this state plus DATA_MANIFEST, MODEL_CONTRACTS, VALIDATION_PLAN, PS_COMPLIANCE and ENGINE_AUDIT before Prompt 2. Preserve the working phase 1 code and raw source hashes. Resolve feasible database checks when Docker becomes available. Obtain/install supported native solver distributions or their complete compiler toolchains and run official examples before constructing site adapters. Finish independent parser/diagnostic work if site inputs remain missing; never invent a Ujjani solver run to fill the gap.

Application setup is demonstrable. Scientific flood simulation, SPH/D-Flow agreement, exposure/loss, GIS exports and Earth Engine assessment remain incomplete.
