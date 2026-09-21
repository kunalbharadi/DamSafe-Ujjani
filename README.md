# DamSafe — Ujjani / Bhima

DamSafe is a traceable dam-release and breach scenario workspace for SIH 2026 Problem Statement 26161 (NTRO). It combines immutable input/scenario records, D-Flow FM regional 2D modelling, DualSPHysics laboratory/near-field modelling, time-varying result visualization, evidence-aware satellite/gauge assessment, and GIS/report export for a bounded Ujjani Dam–Bhima River demonstration.

The local application and retained engine examples are demonstrable. Both engines have genuine benchmark evidence, and a bounded approximate Ujjani D-Flow demonstration exists. The Ujjani model is not calibrated or independently validated; live Earth Engine operation, real exposure/loss assessment, public deployment security, river blockage, and full-domain SPH remain incomplete. Hypothetical dam-break outputs are scenarios, not official forecasts or warnings.

## Start locally

Windows preview (Python 3.12 and Node 24):

```powershell
.\scripts\start.ps1 -Preview
```

This builds the frontend, migrates an explicit SQLite preview database, bootstraps/registers local evidence, starts workers, and serves `http://127.0.0.1:8000`.

PostgreSQL/PostGIS stack (Docker Desktop Linux engine required):

```powershell
docker compose up --build
```

Create `.env` from `.env.example`; do not commit secrets. Numerical runs additionally require the pinned engine images in `config/engine_provenance.json`.

See [environment and credentials](docs/ENVIRONMENT.md) for the exact Earth Engine setup. Local maps and 3D viewers need no API key. The launcher creates a missing .env, and backend processes load it automatically.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
Push-Location frontend; npm.cmd ci; npm.cmd run build; Pop-Location
docker compose config --quiet
```

Native solver tests can skip when Docker/images or retained evidence are unavailable. A skip is not a pass.

## Documentation

Start with the [team quick start](docs/TEAM_ONBOARDING.md) and [current project status](docs/PROJECT_STATUS.md). The [documentation index](docs/README.md) links the product requirements, technical requirements, architecture, backend/API contract, dataset contract, UI/UX guide and ownership map. Contributors and AI tools must follow [AGENTS.md](AGENTS.md).

Local data and state belong under `.local/`, `data/` or `scratch/`; shared large inputs/results should use external storage plus checksummed manifests. Source code is under `backend/damsafe/` and `frontend/src/`; migrations are under `backend/migrations/`; reproducibility and audit scripts are under `scripts/`.
