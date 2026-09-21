# DamSafe Technical Requirements Document

This document describes the repository at 2026-09-16. Versions are resolved from `uv.lock` and `frontend/package-lock.json`.

## Stack

| Area | Resolved technology |
|---|---|
| Runtime/API | Python 3.12–3.13; FastAPI 0.141.1; Uvicorn 0.52.4; Pydantic 2.13.5 |
| Persistence | SQLAlchemy 2.0.52; Alembic 1.20.0; psycopg 3.3.5; PostGIS 16-3.5; SQLite preview |
| GIS/science | Rasterio 1.5.1; Fiona 1.10.1; Shapely 2.1.2; pyproj 3.8.0; netCDF4 1.7.4 |
| Storage | Local or S3-compatible through boto3 1.43.93 |
| Frontend | React/ReactDOM 19.3.0; TypeScript 5.9.3; Vite 7.3.6 |
| Maps/3D | MapLibre GL 6.9.0; proj4 2.22.0; Three.js 0.186.0 |
| Tests | pytest 9.1.1; Ruff 0.16.7; Playwright 1.63.0 |
| Solvers | Pinned D-Flow FM and DualSPHysics identities in `config/engine_provenance.json` |

## Environments and dependencies

- Windows preview: Python 3.12, Node 24/npm, PowerShell and `uv`; SQLite is explicitly preview-only.
- Compose: Docker/Linux containers, PostGIS, migration/bootstrap service, API and audit worker. Engine execution also needs pinned solver images and numerical worker.
- Earth Engine: supported account/project and credential file for live queries. Credentials stay outside Git.

Migrations precede API startup. PostgreSQL/PostGIS is the shared target; SQLite is local preview. Uploaded dataset/scenario input is immutable. Run identity/input is immutable; its state/result is worker-managed. The API must never receive a Docker socket. Numerical workers enforce resource, timeout, cancellation, output-size and path boundaries.

## API, security and storage

`BACKEND_SCHEMA.md` is the REST catalogue. Current endpoints have no user authentication. Trusted-host/same-origin guards and loopback binding make the supplied deployment local-only. Public use is BLOCKED pending authentication, per-project authorization, TLS, CSRF/CORS policy, audit identity, rate limits and managed secrets.

Uploads are streamed, at most 64 MiB, plain-filename only, extension/kind validated, inspected, hashed and stored under generated keys. Local objects default to `.local/objects`; runs to `.local/runs`. S3 mode requires a configured bucket.

## Scientific requirements

- Geographic interchange: WGS84 `EPSG:4326`; current Ujjani computation: `EPSG:32643` metres.
- Every spatial input/output has explicit CRS. Array dimensions alone never establish alignment.
- Elevations need a vertical reference; unknown datum blocks stage/elevation comparison.
- Canonical SI units: m, s, m/s, m³/s, m², m³. Record conversions.
- Timestamps are timezone-aware; preserve source timezone and normalized instant.
- Missing/nodata differs from dry/zero; NOT_REACHED differs from nodata.
- Provenance: agency, URL, licence, acquisition date or explanation, observed/derived/assumed status, synthetic flag, checksum and processing history.

Ingestion supports CSV hydrology, GeoTIFF terrain, and GeoJSON/GeoPackage river/structure/exposure/roughness. Outputs are normalized NetCDF plus GeoTIFF, Shapefile ZIP, KML, GeoJSON, CSV and HTML.

## Engines and jobs

D-Flow FM must retain generated case, native map, solver log, exit state, image/executable identity, normalization hash, diagnostics and product hash. A generated case is not proof of execution. DualSPHysics must retain native particles/logs/manifest and is limited to laboratory/near-field scope. SPH pressure in `sph_adapter.py` is derived from density using a Tait equation and must be labelled derived.

Jobs/runs follow `QUEUED → RUNNING → SUCCEEDED | FAILED | CANCELLED`. Workers claim conditionally. Stale numerical rows fail during recovery. `(project_id, idempotency_key)` prevents duplicate submission. Exports derive only from verified saved results.

## Performance and observability

Result reads are bounded by bbox/frame; area windows permit at most 32 frames. Playback must avoid unbounded arrays. Log stages, progress, time, bounded errors and hashes, never secrets. Measure preprocessing, solver, postprocessing and playback separately on named hardware/domain. Large map/3D code should lazy-load; the current build reports a large MapLibre chunk.

## Environment variables

| Name | Purpose |
|---|---|
| `DAMSAFE_DATABASE_URL` | SQLAlchemy URL; required |
| `DAMSAFE_STORAGE` | `local` or `s3` |
| `DAMSAFE_STORAGE_ROOT` | Local object root |
| `DAMSAFE_RUN_ROOT` | Solver/run root |
| `DAMSAFE_S3_ENDPOINT` | Optional compatible endpoint |
| `DAMSAFE_S3_BUCKET` | S3 bucket |
| `DAMSAFE_DEPLOYMENT_MODE` | Deployment posture declaration |
| `DAMSAFE_REQUIRE_NATIVE_EVIDENCE` | Require native evidence tests |
| `EE_PROJECT` | Earth Engine project ID |
| `EE_SERVICE_ACCOUNT_JSON` | Credential-file path; never commit value/file |
| `POSTGRES_PASSWORD` | Compose DB password; use secret management |

## Tests and definition of done

Contract tests cover validation/immutability; API tests cover isolation, upload, status/recovery; numerical tests cover retained engine output, normalization/products/comparison; observation tests cover provenance and synthetic rejection; browser tests cover navigation. Report all skipped Docker/native tests.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
Push-Location frontend; npm.cmd run build; Pop-Location
docker compose config --quiet
```

| Phase | Definition of done | Current |
|---|---|---|
| Foundation | migrations, immutable inputs, ingestion/readiness, local UI/tests | IMPLEMENTED |
| Engine integration | both pinned engines execute retained benchmarks with logs/normalized output | IMPLEMENTED benchmarks; PARTIAL site |
| Products/UI | bounded APIs, playback, comparison, exports, honest states | PARTIAL |
| Observation | authentic SAR and compatible independent event assessment | BLOCKED |
| Ujjani science | qualified bathymetry/boundaries/forcing, calibration, independent assessment, expert review | BLOCKED |
| Production | auth, backups, monitoring, load/security tests and runbook | PLANNED |

Known risks are absent public auth; missing Ujjani bathymetry/boundaries/gauges/assets; unverified live Earth Engine; fixed demonstration exposure values; no mesh polygons in result API; no Cesium terrain; engine-image dependency; and production qualification of GIS compatibility shims.
