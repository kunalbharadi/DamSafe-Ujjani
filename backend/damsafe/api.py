import hashlib
import json
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import netCDF4
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from pyproj import CRS
from sqlalchemy import func, insert, select, text
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import DatasetInput, EnsembleInput, ProjectInput, RunRequest, ScenarioInput
from .db import datasets, ensembles, engine_for, jobs, now, projects, scenarios, uid
from .ingestion import inspect
from .numerics import products as numerical_products
from .numerics import comparison as numerical_comparison
from .numerics import service as numerical_service
from .numerics.adapters import capabilities
from .numerics.execution import sha256
from .readiness import assess
from .storage import storage_for
from . import exports as numerical_exports
from .observation.gee import ee_service, SARProcessingConfig, ObservationMode
from .observation.import_fallback import import_authentic_observation, ImportedObservationInput
from .observation.comparison import compare_simulation_with_observation
from .observation.gauges import evaluate_gauge_observations
from .observation.exposure import evaluate_exposure
import numpy as np

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
            "phase": "3A",
            "engines": engines(),
        }

    @app.get("/api/projects")
    def list_projects():
        with engine.connect() as conn:
            return [{"id": r.id, **r.body} for r in conn.execute(select(projects))]

    @app.get("/api/projects/{project_id}")
    def project_detail(project_id: str):
        with engine.connect() as conn:
            row = get(conn, projects, project_id)
            return {"id": row["id"], **row["body"]}

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

    @app.get("/api/projects/{project_id}/scenarios/{scenario_id}")
    def scenario_detail(project_id: str, scenario_id: str):
        with engine.connect() as conn:
            row = get(conn, scenarios, scenario_id)
            if row["project_id"] != project_id:
                raise HTTPException(404, "Scenario not found in project")
            return row["body"]

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

    @app.get("/api/projects/{project_id}/runs/{run_id}")
    def run_detail(project_id: str, run_id: str):
        with engine.connect() as conn:
            row = conn.execute(select(numerical_service.runs).where(
                numerical_service.runs.c.id == run_id,
                numerical_service.runs.c.project_id == project_id,
            )).mappings().first()
            if not row:
                raise HTTPException(404, "Run not found in project")
            return dict(row)

    def result_source(project_id, run_id):
        return numerical_service.result_record(engine, project_id, run_id)

    def product_source(source_row, path):
        record = source_row["result"].get("postprocessing", {})
        product = path.with_name("products.nc")
        if (not product.is_file() or not record.get("product_sha256")
                or sha256(product) != record["product_sha256"]
                or record.get("source_normalized_sha256") != source_row["result"]["normalization"]["normalized_sha256"]):
            raise HTTPException(409, "Derived products unavailable or changed")
        with netCDF4.Dataset(product) as ds:
            if getattr(ds, "schema_version", None) != numerical_products.PRODUCT_SCHEMA:
                raise HTTPException(409, "Derived products require schema 2 reprocessing")
        return product

    def metric_bbox(value: str):
        try:
            bbox = tuple(float(part) for part in value.split(","))
            if len(bbox) != 4:
                raise ValueError("Expected four coordinates")
            return bbox
        except ValueError as exc:
            raise HTTPException(422, "bbox must be xmin,ymin,xmax,ymax in the result CRS") from exc

    @app.get("/api/projects/{project_id}/runs/{run_id}/results/metadata")
    def result_metadata(project_id: str, run_id: str):
        row, source, path = result_source(project_id, run_id)
        return numerical_products.metadata(
            path, run_id=run_id, scenario_id=row["input"]["request"].get("scenario_id"),
            configuration_hash=row["input"].get("configuration_hash", "LEGACY_UNHASHED"),
            source_run_id=source["id"], cached=run_id != source["id"],
        )

    @app.get("/api/projects/{project_id}/runs/{run_id}/results/window")
    def result_window(project_id: str, run_id: str, bbox: str, field: str = "h",
                      first_frame: int = 0, frame_count: int = 1):
        _, _, path = result_source(project_id, run_id)
        try:
            return numerical_products.window(path, metric_bbox(bbox), first_frame=first_frame,
                                             frame_count=frame_count, field=field)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/projects/{project_id}/runs/{run_id}/results/series")
    def result_series(project_id: str, run_id: str, cell: int,
                      first_frame: int = 0, frame_count: int | None = None):
        _, _, path = result_source(project_id, run_id)
        try:
            return numerical_products.point_series(path, cell=cell, first_frame=first_frame,
                                                   frame_count=frame_count)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/projects/{project_id}/runs/{run_id}/products/window")
    def derived_window(project_id: str, run_id: str, bbox: str,
                       field: str = "maximum_depth_m"):
        _, source, path = result_source(project_id, run_id)
        try:
            return numerical_products.product_window(product_source(source, path), metric_bbox(bbox), field)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/projects/{project_id}/runs/{run_id}/products/area")
    def flooded_area(project_id: str, run_id: str, first_frame: int = 0, frame_count: int = 32):
        _, source, path = result_source(project_id, run_id)
        if first_frame < 0 or not 1 <= frame_count <= 32:
            raise HTTPException(422, "Area window exceeds 32 frames")
        with netCDF4.Dataset(product_source(source, path)) as ds:
            if first_frame + frame_count > len(ds.dimensions["time"]):
                raise HTTPException(422, "Frame window outside saved result")
            return {"baseline_water": ds.baseline_water, "threshold_m": float(ds.arrival_threshold_m),
                    "area_semantics": ds.area_method,
                    "frames": [{"frame": i, "elapsed_s": float(ds["time"][i]),
                                "flooded_area_m2": float(ds["flooded_area_m2"][i]),
                                "unknown_area_m2": float(ds["unknown_area_m2"][i])}
                               for i in range(first_frame, first_frame + frame_count)]}

    @app.get("/api/projects/{project_id}/runs/{run_id}/products/location")
    def location(project_id: str, run_id: str, name: str, x: float, y: float,
                 radius_m: float, first_frame: int = 0, frame_count: int | None = None):
        _, source, path = result_source(project_id, run_id)
        try:
            return numerical_products.named_location(path, product_source(source, path),
                name=name, x=x, y=y, radius_m=radius_m, first_frame=first_frame,
                frame_count=frame_count)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/projects/{project_id}/runs/{run_id}/compare/{other_run_id}")
    def compare_runs(project_id: str, run_id: str, other_run_id: str):
        first, first_source, first_path = result_source(project_id, run_id)
        second, second_source, second_path = result_source(project_id, other_run_id)
        return numerical_comparison.compare(
            first_path, second_path, product_source(first_source, first_path),
            product_source(second_source, second_path), first, second,
        )

    @app.post("/api/projects/{project_id}/runs/{run_id}/cancel")
    def cancel_run(project_id: str, run_id: str):
        return numerical_service.cancel(engine, project_id, run_id)

    @app.post("/api/projects/{project_id}/ensembles", status_code=202)
    def submit_ensemble(project_id: str, body: EnsembleInput):
        ensemble_id = uid()
        submitted = []
        for variant in body.variants:
            submitted.append(numerical_service.submit(engine, project_id, variant, ensemble_id=ensemble_id))
        record = {
            "id": ensemble_id, "name": body.name, "created_at": now(),
            "variants": [item["input"] for item in submitted],
            "run_ids": [item["id"] for item in submitted],
            "status": "SUCCEEDED" if all(item["state"] == "SUCCEEDED" for item in submitted) else "QUEUED",
            "frequency_semantics": "scenario frequency; not probability or real-world likelihood",
        }
        with engine.begin() as conn:
            get(conn, projects, project_id)
            conn.execute(insert(ensembles).values(id=ensemble_id, project_id=project_id, body=record))
        return record

    @app.get("/api/projects/{project_id}/ensembles")
    def list_ensembles(project_id: str):
        with engine.connect() as conn:
            return records(conn, ensembles, project_id)

    @app.get("/api/projects/{project_id}/ensembles/{ensemble_id}")
    def ensemble_detail(project_id: str, ensemble_id: str):
        with engine.connect() as conn:
            row = get(conn, ensembles, ensemble_id)
            if row["project_id"] != project_id:
                raise HTTPException(404, "Ensemble not found in project")
            return row["body"]

    @app.get("/api/projects/{project_id}/ensembles/{ensemble_id}/summary")
    def ensemble_summary(project_id: str, ensemble_id: str):
        with engine.connect() as conn:
            ensemble = get(conn, ensembles, ensemble_id)
            if ensemble["project_id"] != project_id:
                raise HTTPException(404, "Ensemble not found in project")
            run_rows = [
                dict(row) for row in conn.execute(
                    select(numerical_service.runs).where(
                        numerical_service.runs.c.project_id == project_id,
                        numerical_service.runs.c.id.in_(ensemble["body"]["run_ids"]),
                    )
                ).mappings()
            ]
        products = []
        for row in run_rows:
            if row["state"] != "SUCCEEDED":
                continue
            _, source, path = result_source(project_id, row["id"])
            product = product_source(source, path)
            with netCDF4.Dataset(product) as ds:
                products.append({
                    "run_id": row["id"], "state": row["state"],
                    "extent": np.asarray(ds["cell_state"][:]) == 2,
                    "depth": np.ma.asarray(ds["maximum_depth_m"][:]).filled(np.nan),
                    "arrival": np.ma.asarray(ds["arrival_elapsed_s"][:]).filled(np.nan),
                })
        if not products:
            return {"state": "UNAVAILABLE", "reason": "No successful saved numerical outputs", "runs": run_rows}
        comparable = len({len(item["extent"]) for item in products}) == 1
        if not comparable:
            return {"state": "INCOMPATIBLE", "reason": "Saved output grids have different cell counts",
                    "runs": [item["run_id"] for item in products]}
        intersection = np.logical_and.reduce([item["extent"] for item in products])
        union = np.logical_or.reduce([item["extent"] for item in products])
        depths = np.concatenate([item["depth"][np.isfinite(item["depth"])] for item in products])
        arrivals = np.concatenate([item["arrival"][np.isfinite(item["arrival"])] for item in products])
        return {
            "state": "AVAILABLE", "run_ids": [item["run_id"] for item in products],
            "scenario_frequency": {"tested": len(products), "intersection_cells": int(intersection.sum()),
                                   "union_cells": int(union.sum())},
            "maximum_depth_range_m": [float(np.min(depths)), float(np.max(depths))] if depths.size else None,
            "arrival_time_range_s": [float(np.min(arrivals)), float(np.max(arrivals))] if arrivals.size else None,
            "not_reached_count": int(sum(np.count_nonzero(~np.isfinite(item["arrival"])) for item in products)),
            "settlements": {"state": "UNAVAILABLE", "reason": "No verified settlement exposure dataset"},
            "response_priorities": {"state": "UNAVAILABLE", "reason": "Verified exposure and site results are required"},
        }

    @app.post("/api/projects/{project_id}/runs/{run_id}/exports/{export_format}")
    def export_run(project_id: str, run_id: str, export_format: str):
        row, source, path = result_source(project_id, run_id)
        product = product_source(source, path)
        try:
            output = numerical_exports.create_export(
                path, product, numerical_service.run_root() / "exports" / project_id / run_id,
                run_id, export_format, metadata=row["result"],
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return FileResponse(output, filename=output.name)

    @app.get("/api/projects/{project_id}/runs/{run_id}/exports/{export_format}/verify")
    def verify_run_export(project_id: str, run_id: str, export_format: str):
        row, source, path = result_source(project_id, run_id)
        product = product_source(source, path)
        output = numerical_exports.create_export(
            path, product, numerical_service.run_root() / "exports" / project_id / run_id,
            run_id, export_format, metadata=row["result"],
        )
        return numerical_exports.verify_export(output, export_format)

    # --- Phase 4 Observation & Earth Engine Endpoints ---

    @app.post("/api/observation/gee/query")
    def query_gee_observation(
        site_key: str = "ujjani-bhima",
        mode: ObservationMode = ObservationMode.HISTORICAL_EVENT,
        target_time: str | None = None,
        bounds_wgs84: tuple[float, float, float, float] = (74.6, 18.0, 75.1, 18.4),
    ):
        return ee_service.query_sentinel1(
            site_key=site_key,
            bounds_wgs84=bounds_wgs84,
            mode=mode,
            target_time=target_time,
        )

    @app.post("/api/observation/import")
    def import_observation(body: ImportedObservationInput):
        return import_authentic_observation(body)

    @app.post("/api/projects/{project_id}/runs/{run_id}/compare_satellite")
    def compare_satellite(
        project_id: str,
        run_id: str,
        mode: ObservationMode = ObservationMode.HISTORICAL_EVENT,
        target_time: str | None = None,
    ):
        row, source, path = result_source(project_id, run_id)
        product = product_source(source, path)
        with netCDF4.Dataset(product) as ds:
            cell_states = np.asarray(ds["cell_state"][:])
            if cell_states.ndim == 1:
                wet_matrix = [[1 if cell == 2 else 0 for cell in cell_states]]
            else:
                wet_matrix = [[1 if cell == 2 else 0 for cell in row] for row in cell_states]

        obs = ee_service.query_sentinel1(
            site_key="ujjani-bhima",
            bounds_wgs84=(74.6, 18.0, 75.1, 18.4),
            mode=mode,
            target_time=target_time,
        )
        return compare_simulation_with_observation(
            run_id=run_id,
            sim_grid=wet_matrix,
            observation=obs,
            sim_frame_time=target_time or obs.acquisition_time,
        )

    @app.get("/api/projects/{project_id}/runs/{run_id}/gauges/{station_id}")
    def evaluate_gauge(project_id: str, run_id: str, station_id: str):
        return evaluate_gauge_observations(station_id, run_id)

    @app.get("/api/projects/{project_id}/runs/{run_id}/exposure")
    def evaluate_exposure_endpoint(project_id: str, run_id: str):
        return evaluate_exposure(run_id, "ujjani-bhima")

    dist = ROOT / "frontend/dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        if not (dist / "index.html").exists():
            raise HTTPException(503, "Build frontend with npm run build in frontend/")
        return FileResponse(dist / "index.html")

    return app
