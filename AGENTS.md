# DamSafe Contributor and AI-Agent Instructions

## Mission and fixed scope

DamSafe addresses SIH PS 26161 with traceable scenario-based dam release/breach modelling, D-Flow FM regional output, DualSPHysics near-field output, GIS visualization/export, and evidence-aware assessment. The demonstration site is Ujjani Dam and a bounded Bhima reach. It is not an operational warning system.

## Repository map

- `backend/damsafe/`: API, contracts, persistence, storage, workers, numerics, observation and site logic.
- `backend/tests/`: backend, scientific-contract, security and evidence tests.
- `backend/migrations/`: Alembic schema revisions.
- `frontend/src/`: React pages, components, maps and Three.js viewers.
- `scripts/`: bootstrap, audits, evidence registration and engine utilities.
- `config/`: site and pinned engine provenance.
- `docs/`: requirements, architecture, contracts, status and evidence.
- `.local/`, `data/`, `scratch/`: untracked local data/results; confirm licences before sharing.

## Before editing

Read `docs/README.md`, `docs/PROJECT_STATUS.md`, the relevant contract/design document, `git status --short`, and all target files. Search for existing implementations and tests. Preserve unrelated dirty-worktree changes. Coordinate before editing files owned by another active contributor.

## Commands

```powershell
# full local preview
.\scripts\start.ps1 -Preview

# backend API only after env/migrations
.\.venv\Scripts\python.exe -m uvicorn damsafe.api:create_app --factory --host 127.0.0.1 --port 8000

# checks
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
Push-Location frontend; npm.cmd ci; npm.cmd run build; Pop-Location
docker compose config --quiet
```

For the shared PostGIS stack use `docker compose up --build`; it requires a running Docker Linux engine. Run `alembic upgrade head` before API startup. Never run expensive simulations merely to validate documentation.

## Shared-work rules

Use short branches such as `frontend/results-map`, `backend/run-contract`, `gis/ujjani-inputs`, or `docs/status-audit`. Prefer conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) with one coherent purpose. Do not commit generated data, secrets or another member’s unfinished changes. Never reset, overwrite, reformat or delete unrelated work. Before commit, inspect the diff, run relevant tests and update the source-of-truth docs.

Ownership areas are defined in `docs/TEAM_RESPONSIBILITIES.md`. Cross-area contract, scientific method, schema, public claim and UI status changes require review from the affected owners.

## Scientific integrity

- Never fabricate Ujjani coordinates, inputs, discharge, flood results, accuracy, impact, population, loss or routes.
- A file, adapter, UI, fixture or skipped test does not prove a feature ran.
- Never silently fall back from a real engine to mock/synthetic output.
- Label every result as local solver, imported solver, synthetic fixture, frontend-only visualization or planned.
- Keep `OBSERVED`, `DERIVED`, `ASSUMED` and `SYNTHETIC` explicit.
- Inter-model agreement is not real-world accuracy.
- Assess satellite/gauge evidence only for compatible place, event time, forcing, datum/baseline, grid and quality.
- A hypothetical breach cannot receive an observed-event validation claim from an unrelated monsoon image.
- Preserve WET/DRY/NODATA/NOT_REACHED distinctions and units/CRS/datum.

## Secrets and data

For credential setup use `docs/ENVIRONMENT.md`. The root file is deliberately named `AGENTS.md`, the recognized agent-instruction filename; do not create a divergent `agent.md` copy. Native geospatial import failures must fail explicitly, never install an approximate replacement silently.

Create `.env` from `.env.example`; never commit it, credential JSON, tokens or secret values. Do not print `.env`. Large rasters, satellite scenes, DBs, native engine outputs and exports stay outside Git. Track small redistributable examples only with source URL, licence, checksum and classification; otherwise add a manifest/fetch instruction.

## Definition of done and handover

Work is done when behavior is implemented, relevant tests pass, failure/empty states are handled, provenance/classification remains accurate, docs are updated and the diff contains no unrelated work. A skip is reported as a skip.

Every contributor or AI agent hands over:

- files changed;
- behavior and reason;
- commands run;
- tests passed and failed;
- tests skipped and why;
- blockers and external inputs;
- assumptions;
- whether results/evidence are real local solver, imported, synthetic, frontend-only or planned.
