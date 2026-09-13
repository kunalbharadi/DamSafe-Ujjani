# DamSafe — Ujjani / Bhima

Phase 2 implementation for SIH PS 26161. The application imports and audits inputs, saves immutable scenarios, and runs bounded background readiness and numerical jobs. Locally built D-Flow FM and DualSPHysics CPU engines have executed official examples and a physically matched synthetic dam-break benchmark. **No verified Ujjani flood prediction, computed breach or Ujjani two-engine comparison exists.** See [phase 2 evidence](docs/PHASE2_EVIDENCE.md).

This `DAM` directory is the project root. The user-supplied build sequence is preserved unchanged in `DamSafe_Ujjani_Four_Codex_Prompts.md`; phase 1 evidence must be reviewed before phase 2. `kunal.md` was preserved. The supplied brief is in `docs/SUPPLIED_BRIEF.txt`; the full PRD referred to as `Pasted markdown(6).md` was not present.

## Start locally

From PowerShell in this directory:

```powershell
# Tested Windows setup preview: Python 3.12 + Node 24
.\scripts\start.ps1 -Preview
```

Open http://127.0.0.1:8000. The script installs locked dependencies, builds the UI, runs migrations, seeds the Ujjani configuration and starts the API, audit worker and numerical worker. Ctrl+C stops the processes. Preview uses persistent SQLite and local files in `.local/`, and displays **SQLITE PREVIEW**. Numerical examples additionally require the locally installed hash-pinned Docker engine image. It is explicitly different from the PostgreSQL deployment.

```powershell
# PostgreSQL/PostGIS stack; requires a running Docker Desktop Linux engine
.\scripts\start.ps1
```

Docker Compose PostGIS 16/3.5 and migrations have been exercised locally. The default Compose API/worker containers do not have Docker access, so engine examples are available through the host preview or a separately configured host API/numerical worker; engine capability checks truthfully return unavailable inside the default Compose API. `compose.numerics.yaml` can publish PostgreSQL to loopback for that host setup. The only default published port binds to `127.0.0.1`. `.env.example` documents local development settings.

## What to use

- **Overview:** project status and an intentionally unset study domain.
- **Data library:** raw-file upload with a JSON provenance contract, a new immutable version for every successful import, and audit findings. Source files stay unchanged.
- **Scenarios:** save incomplete drafts as immutable snapshots; review missing conditions before any future execution. The JSON editor is a phase 1 technical setup interface.
- **Readiness:** synchronous snapshot audits or durable worker jobs. A SUCCEEDED audit is not a successful simulation or validation claim.
- **Numerical runs:** inspect local engine availability and queue official laboratory examples in a separate synthetic project. Ujjani site submissions remain blocked by missing physical inputs.
- **API reference:** http://127.0.0.1:8000/docs. `POST/GET /api/projects/{id}/runs` and cancellation report execution separately from validation.

See [input contracts](docs/MODEL_CONTRACTS.md) for examples and [data manifest](docs/DATA_MANIFEST.md) for the real NWIC files. Those raw files were retrieved and audited; they are not yet verified aggregate river-outflow hydrographs.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
Push-Location frontend
npm.cmd ci
npm.cmd run build
npm.cmd audit
Pop-Location
docker compose config --quiet
```

Python dependencies and hashes are in `uv.lock`; browser dependencies are in `frontend/package-lock.json`. CPython 3.12 is selected through `py -3.12` rather than the MSYS Python first on this computer's PATH.

## Layout and persistence

`backend/damsafe/` contains contracts, ingestion, readiness, API, storage and worker modules. Alembic manages the database. The durable audit queue uses the same SQL database with atomic claims and cancellation, avoiding a separate Redis service for small readiness jobs. SQLAlchemy supports the proposed PostgreSQL deployment; the explicit SQLite preview supports local development when Docker is unavailable. PostGIS extension setup exists, but spatial SQL and PostgreSQL concurrency remain unverified. Vector inspection currently uses Fiona/Shapely.

Raw inputs and outputs, `.env`, native binaries and `.local/` are ignored by Git; selected compact run manifests and build logs are under `docs/evidence/phase2/`. No Git repository existed initially; no commits, pushes, merges or deployment were performed. The S3 upload/delete interface is configurable through standard AWS environment credentials; no S3 service was exercised.

Continue from [PROJECT_STATE](docs/PROJECT_STATE.md) and the [evidence table](docs/PHASE2_EVIDENCE.md). Site predictions remain blocked by verified physical inputs and a completed D-Flow/site comparison path.
