import hashlib
import json
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from pyproj import CRS
from sqlalchemy import func, insert, select, text
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import DatasetInput, ProjectInput, RunRequest, ScenarioInput
from .db import datasets, engine_for, jobs, now, projects, scenarios, uid
from .ingestion import inspect
from .numerics import service as numerical_service
from .numerics.adapters import capabilities
from .readiness import assess
from .storage import storage_for

ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD = 64 * 1024 * 1024


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(body):
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def engines():
    return [capabilities(name) for name in ("dflowfm", "dualsphysics")]


def create_app(database_url=None, storage=None):
    engine = engine_for(database_url)
    store = storage or storage_for()

    @asynccontextmanager
    async def lifespan(app):
        with engine.connect() as conn:
            conn.execute(select(projects.c.id).limit(1))  # migrations must run explicitly
        yield
        engine.dispose()

    app = FastAPI(title="DamSafe · Foundation", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

    @app.middleware("http")
    async def local_browser_guard(request, call_next):
        origin = request.headers.get("origin")
        same_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin not in {
            same_origin,
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        }:
            return JSONResponse({"detail": "Untrusted browser origin"}, status_code=403)
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > MAX_UPLOAD or int(length) < 0:
                    return JSONResponse({"detail": "Request exceeds 64 MiB upload limit"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        return await call_next(request)

    def get(conn, table, ident):
        row = conn.execute(select(table).where(table.c.id == ident)).mappings().first()
        if row is None:
            raise HTTPException(404, "Record not found")
        return dict(row)

    def records(conn, table, project_id):
        get(conn, projects, project_id)
        return [
            dict(r) for r in conn.execute(select(table).where(table.c.project_id == project_id)).mappings()
        ]

    @app.get("/api/health")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            postgis = (
                conn.execute(text("SELECT PostGIS_Version()")).scalar()
                if engine.dialect.name == "postgresql"
                else None
            )
        return {
            "status": "ok",
            "database": engine.dialect.name,
            "postgis": postgis,
            "preview": engine.dialect.name == "sqlite",
            "phase": 2,
            "engines": engines(),
        }

    @app.get("/api/projects")
    def list_projects():
        with engine.connect() as conn:
            return [{"id": r.id, **r.body} for r in conn.execute(select(projects))]

    @app.post("/api/projects", status_code=201)
    def add_project(body: ProjectInput):
        if body.computation_crs:
            try:
                CRS.from_user_input(body.computation_crs)
            except Exception as e:
                raise HTTPException(422, "Unrecognized computation CRS") from e
        ident = uid()
        with engine.begin() as conn:
            conn.execute(insert(projects).values(id=ident, body=body.model_dump(mode="json")))
        return {"id": ident, **body.model_dump(mode="json")}

    @app.get("/api/projects/{project_id}/datasets")
    def list_datasets(project_id: str):
        with engine.connect() as conn:
            return [r["body"] for r in records(conn, datasets, project_id)]

    @app.post("/api/projects/{project_id}/datasets", status_code=201)
    async def upload(
        project_id: str, request: Request, filename: str, metadata_json: str = Query(max_length=16000)
    ):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,150}", filename) or ".." in filename:
            raise HTTPException(422, "Use a plain filename without paths or traversal")
        ext = Path(filename).suffix.lower()
        if ext not in {".csv", ".tif", ".tiff", ".geojson", ".gpkg"}:
            raise HTTPException(415, "Allowed formats: CSV, GeoTIFF, GeoJSON, GeoPackage")
        try:
            spec = DatasetInput.model_validate_json(metadata_json)
        except ValidationError as e:
            raise HTTPException(422, str(e)) from e
        expected = (
            {".csv"}
            if spec.kind == "hydrology"
            else {".tif", ".tiff"}
            if spec.kind == "terrain"
            else {".geojson", ".gpkg"}
        )
        if ext not in expected:
            raise HTTPException(422, "File format does not match dataset kind")
        with engine.connect() as conn:
            project = get(conn, projects, project_id)["body"]
        if project["synthetic"] != spec.provenance.synthetic:
            raise HTTPException(422, "Synthetic fixtures must remain in a separate synthetic project")
        ident = uid()
        key = f"{project_id}/{ident}{ext}"
        count, checksum = 0, hashlib.sha256()
        with tempfile.TemporaryDirectory(prefix="damsafe-") as tmp:
            path = Path(tmp) / f"upload{ext}"
            with path.open("wb") as out:
                async for chunk in request.stream():
                    count += len(chunk)
                    if count > MAX_UPLOAD:
                        raise HTTPException(413, "Upload exceeds 64 MiB")
                    checksum.update(chunk)
                    out.write(chunk)
            if count == 0:
                raise HTTPException(422, "Empty upload")
            try:
                inspection = await run_in_threadpool(inspect, path, spec)
            except Exception as e:
                raise HTTPException(422, f"Dataset rejected: {str(e)[:1000]}") from e
            await run_in_threadpool(store.put, key, path)
        body = {
            **spec.model_dump(mode="json"),
            "id": ident,
            "project_id": project_id,
            "storage_key": key,
            "original_filename": filename,
            "bytes": count,
            "sha256": checksum.hexdigest(),
            "retrieved_at": now(),
            "inspection": inspection,
        }
        try:
            with engine.begin() as conn:
                # Serialize version allocation per project, including PostgreSQL concurrency.
                conn.execute(projects.update().where(projects.c.id == project_id).values(body=project))
                version = (
                    conn.execute(
                        select(func.max(datasets.c.version)).where(
                            datasets.c.project_id == project_id, datasets.c.name == spec.name
                        )
                    ).scalar()
                    or 0
                )
                body["version"] = version + 1
                conn.execute(
                    insert(datasets).values(
                        id=ident, project_id=project_id, name=spec.name, version=version + 1, body=body
                    )
                )
        except Exception:
            store.delete(key)
            raise
        return body

    @app.get("/api/projects/{project_id}/scenarios")
    def list_scenarios(project_id: str):
        with engine.connect() as conn:
            return [r["body"] for r in records(conn, scenarios, project_id)]

    @app.post("/api/projects/{project_id}/scenarios", status_code=201)
    def add_scenario(project_id: str, body: ScenarioInput):
        with engine.begin() as conn:
            project = get(conn, projects, project_id)["body"]
            available = {r["id"]: r["body"] for r in records(conn, datasets, project_id)}
            if any(i not in available for i in body.dataset_ids):
                raise HTTPException(422, "Every dataset must belong to this project")
            if (
                body.forcing.mode == "prescribed_release"
                and body.forcing.hydrograph_dataset_id
                and body.forcing.hydrograph_dataset_id not in body.dataset_ids
            ):
                raise HTTPException(422, "Hydrograph must be included in snapshot dataset_ids")
            chosen = [available[i] for i in body.dataset_ids]
            assumed = body.assumptions or any(d["provenance"]["status"] == "assumed" for d in chosen)
            assumed = assumed or any(
                getattr(body, f) and getattr(body, f).status == "assumed"
                for f in (
                    "initial_river_state",
                    "downstream_boundary",
                    "tributary_inflows",
                    "structure_treatment",
                    "roughness",
                )
            )
            assumed = (
                assumed
                or body.forcing.mode == "computed_breach"
                or not getattr(body.forcing, "historical", False)
            )
            mode = "SYNTHETIC" if project["synthetic"] else "MIXED_ASSUMPTIONS" if assumed else "OBSERVED"
            snapshot = {
                "contract_version": 1,
                "project": project,
                "scenario": body.model_dump(mode="json"),
                "datasets": chosen,
                "input_mode": mode,
            }
            ident = uid()
            record = {
                "id": ident,
                "name": body.name,
                "created_at": now(),
                "sha256": digest(snapshot),
                "snapshot": snapshot,
                "evidence_status": "UNASSESSED",
            }
            conn.execute(insert(scenarios).values(id=ident, project_id=project_id, body=record))
        return record

    @app.get("/api/projects/{project_id}/readiness")
    def readiness(project_id: str, scenario_id: str | None = None):
        with engine.connect() as conn:
            project = get(conn, projects, project_id)["body"]
            items = [r["body"] for r in records(conn, datasets, project_id)]
            scenario = None
            if scenario_id:
                record = get(conn, scenarios, scenario_id)
                if record["project_id"] != project_id:
                    raise HTTPException(404, "Scenario not found in project")
                snap = record["body"]["snapshot"]
                project, items = snap["project"], snap["datasets"]
                scenario = ScenarioInput.model_validate(snap["scenario"])
            return assess(project, items, scenario)

    @app.post("/api/projects/{project_id}/readiness-jobs", status_code=202)
    def readiness_job(project_id: str):
        with engine.begin() as conn:
            project = get(conn, projects, project_id)["body"]
            items = [r["body"] for r in records(conn, datasets, project_id)]
            ident = uid()
            body = {
                "kind": "READINESS_AUDIT",
                "created_at": now(),
                "project": project,
                "datasets": items,
                "note": "This job audits inputs; it does not run a hydraulic solver.",
            }
            conn.execute(insert(jobs).values(id=ident, project_id=project_id, state="QUEUED", body=body))
        return {"id": ident, "state": "QUEUED"}

    @app.get("/api/projects/{project_id}/jobs")
    def get_jobs(project_id: str):
        with engine.connect() as conn:
            return records(conn, jobs, project_id)

    @app.post("/api/projects/{project_id}/jobs/{job_id}/cancel")
    def cancel_job(project_id: str, job_id: str):
        with engine.begin() as conn:
            job = get(conn, jobs, job_id)
            if job["project_id"] != project_id:
                raise HTTPException(404, "Job not found")
            result = conn.execute(
                jobs.update()
                .where(jobs.c.id == job_id, jobs.c.state.in_(["QUEUED", "RUNNING"]))
                .values(state="CANCELLED")
            )
            if result.rowcount != 1:
                raise HTTPException(409, "Job already terminal")
        return {"id": job_id, "state": "CANCELLED"}

    @app.post("/api/projects/{project_id}/runs", status_code=202)
    def submit_run(project_id: str, body: RunRequest):
        return numerical_service.submit(engine, project_id, body)

    @app.get("/api/projects/{project_id}/runs")
    def list_runs(project_id: str):
        return numerical_service.get_runs(engine, project_id)

    @app.post("/api/projects/{project_id}/runs/{run_id}/cancel")
    def cancel_run(project_id: str, run_id: str):
        return numerical_service.cancel(engine, project_id, run_id)

    dist = ROOT / "frontend/dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        if not (dist / "index.html").exists():
            raise HTTPException(503, "Build frontend with npm run build in frontend/")
        return FileResponse(dist / "index.html")

    return app
