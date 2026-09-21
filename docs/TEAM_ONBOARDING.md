# Team Member Quick Start

DamSafe turns traceable terrain, hydrology and scenario inputs into saved hydrodynamic results and GIS deliverables. D-Flow FM covers regional 2D flow; DualSPHysics covers laboratory/near-field particle flow. The current software is demonstrable locally, while a scientifically assessed Ujjani event is still blocked by field data and independent observations.

## Setup

Required: Git, Python 3.12, Node.js 24/npm, PowerShell, and `uv`; Docker Desktop with Linux containers for PostGIS and real engine execution. Copy `.env.example` to `.env` and edit locally. Never commit or paste its values into logs.

Fastest Windows preview:

```powershell
.\scripts\start.ps1 -Preview
```

This syncs locked Python packages, installs/builds the frontend, migrates SQLite preview, bootstraps the project, registers retained examples, starts audit/numerical workers, and serves `http://127.0.0.1:8000`.

Shared stack:

```powershell
docker compose up --build
```

Engine availability appears at `GET /api/health` and on Simulation. Availability is separate from a successful run. Pinned engine identities are in `config/engine_provenance.json`.

## Data and checks

Put large/raw data in ignored `data/`, local object/run state in `.local/`, and experiments in `scratch/`. Use `docs/DATASET_SCHEMA.md` and manifests rather than sharing opaque files.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
Push-Location frontend; npm.cmd run build; Pop-Location
docker compose config --quiet
```

Choose an ownership area in `TEAM_RESPONSIBILITIES.md`, inspect `git status`, read the relevant code/tests/docs, create a focused branch, make small changes, run relevant checks, inspect the diff and provide the AGENTS.md handover. Do not “fix” another person’s dirty changes without coordination.

## Reading guide

- New everyone: `README.md`, `PROJECT_STATUS.md`, this guide.
- Product/UI: `PRD.md`, `UI_UX_GUIDE.md`.
- Backend/integration: `TRD.md`, `ARCHITECTURE.md`, `BACKEND_SCHEMA.md`.
- GIS/science: `DATASET_SCHEMA.md`, `MODEL_CONTRACTS.md`, `VALIDATION_PLAN.md`.
- Demo/review: `FINAL_READINESS.md`, `DEMO_SCRIPT.md`, `JUDGE_QA.md`.

## Common problems

- **Database URL error:** use the preview script or set `DAMSAFE_DATABASE_URL` before migration/start.
- **Docker/engine unavailable:** start Docker Linux engine and build/install pinned images; report solver tests as skipped meanwhile.
- **Port 8000 occupied:** stop the existing local server or use a different Uvicorn port; frontend proxy assumes 8000.
- **Earth Engine unconfigured:** set only documented variable names locally; a scene query remains unverified until credentials and processing succeed.
- **GIS native-library failure:** reinstall locked wheels; `geo_compat.py` is a constrained compatibility path, not proof of production equivalence.
- **No Ujjani result/impact:** verify project selection and retained artifacts; never substitute synthetic values.

## 15-minute checklist

- [ ] Read project status and scientific-claim limits.
- [ ] Inspect the worktree and choose an unowned task.
- [ ] Install Python/Node dependencies from locks.
- [ ] Create local `.env` without committing it.
- [ ] Start preview and open the nine-page workflow.
- [ ] Check `/api/health` and engine availability.
- [ ] Run one relevant test/build command.
- [ ] Locate your data/code/docs ownership paths.
- [ ] Agree on handover and review needs before editing shared contracts.
