# Documentation Audit

**Audit date:** 2026-09-16  
**Scope:** official developer documentation set requested for DamSafe. No application code, data, migration, simulation or UI behavior was changed.

## Files created or consolidated

- Updated/replaced: root `README.md`, `docs/PRD.md`, `docs/TRD.md`.
- Created: root `AGENTS.md`; `docs/ARCHITECTURE.md`, `BACKEND_SCHEMA.md`, `DATASET_SCHEMA.md`, `UI_UX_GUIDE.md`, `TEAM_ONBOARDING.md`, `TEAM_RESPONSIBILITIES.md`, `PROJECT_STATUS.md`, `README.md`, and this audit.
- Existing phase/evidence/readiness documents were preserved. They are supporting history; `PROJECT_STATUS.md` is the current status authority.

## Repository areas inspected

Backend API/contracts/database/migrations, ingestion/readiness/storage, audit and numerical workers, both engine adapters/provenance, normalization/products/comparison/exports, Ujjani/breach/terrain code, Earth Engine/SAR/import/gauge/exposure code, backend tests, frontend root/types/API/pages/components/viewers/tests, Docker/Compose, environment template, setup/audit/engine scripts, Python and npm locks, site/engine configuration, all existing documentation headings/content and retained evidence manifests/logs.

## Verified facts

- Resolved stack versions in TRD come from current lockfiles.
- Six export routes/formats are implemented.
- Database immutability and run idempotency constraints exist.
- Run states are queued/running/succeeded/failed/cancelled; local/imported and evidence/input modes are explicit contracts.
- Retained evidence records genuine D-Flow FM and DualSPHysics benchmark execution.
- The Ujjani case remains an approximate bounded demonstration, not calibrated/independently validated.
- SPH browser frames use saved particles; regional UI results use normalized 2D output.
- Current endpoints are unauthenticated and supplied deployment is loopback/local-demo oriented.

## Contradictions corrected

- Existing TRD listed obsolete React/Vite/TypeScript/Three versions and packages no longer installed.
- Existing readiness text claimed full PS compliance and scientific validation beyond the verified evidence.
- Cesium/regional terrain and MapLibre polygon rendering were described too strongly; current code uses Three.js and geographic cell centres.
- Sentinel-1 scene/query/processing components were conflated with a qualified historical validation and live near-real-time execution.
- Exposure output was described as an implemented overlay although `exposure.py` returns fixed demonstration values.
- Some export descriptions called point features flood polygons; current exporter writes result-cell points for vector formats.

## Unresolved questions / teammate inputs

- Primary authoritative sources/licences for coded Ujjani dam values and local terrain files.
- Surveyed bathymetry/cross-sections, structures, spatial roughness and qualified boundary/forcing series.
- Exact retained Ujjani run distribution/registration procedure for a fresh clone.
- Independent gauge series and authentic time-compatible Sentinel-1 observation package; whether a live Earth Engine account is available.
- Licensed settlement/building/road/facility/population/agriculture data and approved impact methodology.
- Named role assignments, production hosting target, identity provider and security owner.
- Domain-expert review and sponsor clarification of the required two-engine site-comparison scope.

## Commands executed

- `git status --short`
- `rg --files` and targeted `rg` searches over code, tests, environment names, routes, schemas and documentation
- read-only `Get-Content` inspection of repository files and evidence
- `.venv\Scripts\python.exe -m uv tree --locked --depth 1`
- Node read of resolved frontend package-lock versions
- Documentation link/path, secret-pattern and contradiction checks (results below)
- Relevant lightweight test/build/lint commands (results below)

## Checks

| Check | Result |
|---|---|
| Requested files present | PASS: all 13 root/docs targets exist |
| Documentation-set relative Markdown targets | PASS |
| `git diff --check` on documentation set | PASS |
| Secret-pattern audit | PASS: no embedded credential-like assignment found |
| Stale-version/overclaim search in documentation set | PASS |
| Frontend production build | PASS: TypeScript and Vite 7.3.6; warning for chunks above 500 kB |
| `docker compose config --quiet` | PASS |
| Backend pytest | BLOCKED during collection: Windows Application Control rejected the native `netCDF4._netCDF4` DLL; no test result claimed |
| Ruff | FAIL: 175 pre-existing issues in application/test files; documentation-only scope made no source fixes |
| Commit/push/deploy | NOT PERFORMED |

The relative-link audit was limited to this official documentation set. Several retained older reports use valid local `file:///` links; a simple relative-link checker reports those as non-relative and they were not rewritten in this task.

No `.env` values or credentials were read or copied. Only environment-variable names from `.env.example` and code were documented.
