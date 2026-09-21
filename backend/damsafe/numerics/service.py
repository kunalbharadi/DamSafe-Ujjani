import hashlib
import json
import os
from pathlib import Path

import netCDF4
from fastapi import HTTPException
from sqlalchemy import insert, select

from ..contracts import RunRequest
from ..db import datasets, now, projects, runs, scenarios, uid
from .adapters import ROOT, SOURCES, capabilities
from .execution import sha256
from .products import PRODUCT_SCHEMA


def configuration_hash(
    request: RunRequest,
    capability: dict,
    snapshot: dict | None = None,
    site_config: object | None = None,
):
    """Identity covers solver image, physical input file set and configuration."""
    profile = SOURCES[request.engine]
    source = ROOT / "external" / profile["directory"]
    if request.case_kind == "SITE_SCENARIO":
        identity = {
            "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
            "engine_image_id": capability["image_id"],
            "source_commit": profile["commit"],
            "case_kind": "SITE_SCENARIO",
            "snapshot": snapshot or {},
            "site_configuration": (
                site_config.model_dump(mode="json")
                if hasattr(site_config, "model_dump")
                else (site_config or {})
            ),
        }
    elif request.engine == "dualsphysics":
        files = [source / "examples/main/01_DamBreak/CaseDambreakVal2D_Def.xml"]
        identity = {
            "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
            "engine_image_id": capability["image_id"],
            "source_commit": profile["commit"],
            "source_files": {p.relative_to(source).as_posix(): sha256(p) for p in files},
        }
    else:
        case = source / "examples/dflowfm/01_dflowfm_sequential"
        files = sorted(p for p in case.rglob("*") if p.is_file() and p.suffix.lower() not in {".sh", ".bat"})
        identity = {
            "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
            "engine_image_id": capability["image_id"],
            "source_commit": profile["commit"],
            "source_files": {p.relative_to(source).as_posix(): sha256(p) for p in files},
        }
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _valid_cached_source(row):
    if row["state"] != "SUCCEEDED" or row["result"].get("cached_from_run_id"):
        return False
    expected = row["result"].get("normalization", {}).get("normalized_sha256")
    path = run_root() / row["id"] / "normalized.nc"
    if not expected or not path.is_file() or sha256(path) != expected:
        return False
    products = row["result"].get("postprocessing")
    if not products:
        return False  # older runs need verified product backfill before reuse
    product_path = path.with_name("products.nc")
    if not (products.get("source_normalized_sha256") == expected
            and products.get("product_sha256") and product_path.is_file()
            and sha256(product_path) == products["product_sha256"]):
        return False
    with netCDF4.Dataset(product_path) as ds:
        return getattr(ds, "schema_version", None) == PRODUCT_SCHEMA


def result_record(engine, project_id, run_id):
    with engine.connect() as conn:
        row = conn.execute(select(runs).where(runs.c.id == run_id, runs.c.project_id == project_id)).mappings().first()
        if not row:
            raise HTTPException(404, "Numerical run not found in project")
        if row["state"] != "SUCCEEDED":
            raise HTTPException(409, {"state": row["state"], "result": row["result"]})
        source_id = row["result"].get("cached_from_run_id", run_id)
        source = conn.execute(select(runs).where(runs.c.id == source_id, runs.c.project_id == project_id)).mappings().first()
        if not source or source["state"] != "SUCCEEDED":
            raise HTTPException(409, "Source run is not successful")
        if row["input"].get("configuration_hash") != source["input"].get("configuration_hash"):
            raise HTTPException(409, "Cached source configuration mismatch")
        if row["input"].get("request", {}).get("scenario_id") != source["input"].get("request", {}).get("scenario_id"):
            raise HTTPException(409, "Cached source scenario mismatch")
        path = run_root() / source_id / "normalized.nc"
        expected = source["result"].get("normalization", {}).get("normalized_sha256")
        if not path.is_file() or not expected or sha256(path) != expected:
            raise HTTPException(409, "Saved numerical result is unavailable or changed")
        return dict(row), dict(source), path


def run_root():
    path = Path(os.environ.get("DAMSAFE_RUN_ROOT", ".local/runs")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def submit(engine, project_id, request: RunRequest, ensemble_id: str | None = None):
    with engine.begin() as conn:
        project = conn.execute(select(projects).where(projects.c.id == project_id)).mappings().first()
        if not project:
            raise HTTPException(404, "Project not found")
        old = (
            conn.execute(
                select(runs).where(
                    runs.c.project_id == project_id, runs.c.idempotency_key == request.idempotency_key
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["input"]["request"] != request.model_dump(mode="json"):
                raise HTTPException(409, "Idempotency key already belongs to a different request")
            return dict(old)
        snap = None
        site_config = None
        site_key = None
        if request.case_kind == "SITE_SCENARIO":
            row = (
                conn.execute(
                    select(scenarios).where(
                        scenarios.c.id == request.scenario_id, scenarios.c.project_id == project_id
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                raise HTTPException(422, "Select an immutable scenario in this project")
            snap = row["body"]["snapshot"]

            # Load and validate generic site configuration
            from ..site.configuration import load_site_configuration

            proj_dict = project["body"]
            site_key = proj_dict.get("site_key") or "ujjani-bhima"
            try:
                site_config = load_site_configuration(site_key, proj_dict)
            except Exception as exc:
                raise HTTPException(422, f"Site configuration could not be resolved: {exc}") from exc

            # Validate spatial definition
            if not site_config.spatial.computation_crs:
                raise HTTPException(422, "Site computation CRS is missing")
            if not site_config.spatial.river_centerline_wgs84 or len(site_config.spatial.river_centerline_wgs84) < 2:
                raise HTTPException(422, "Site river centerline requires at least 2 coordinate points")
            w, s, e, n = site_config.spatial.bounds_wgs84
            if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
                raise HTTPException(422, "Invalid site WGS84 bounding box coordinates")

            # Validate scenario times if present
            scen_body = snap.get("scenario") or snap
            start_str = scen_body.get("start_time")
            end_str = scen_body.get("end_time")
            if start_str and end_str:
                try:
                    from datetime import datetime
                    t0 = datetime.fromisoformat(str(start_str))
                    t1 = datetime.fromisoformat(str(end_str))
                    if t1 <= t0:
                        raise HTTPException(422, "Scenario end_time must follow start_time")
                except ValueError as exc:
                    raise HTTPException(422, f"Invalid scenario datetime values: {exc}") from exc

            # Validate referenced datasets if specified in scenario
            ds_ids = scen_body.get("dataset_ids") or []
            if ds_ids:
                proj_datasets = {
                    r["id"]
                    for r in conn.execute(
                        select(datasets.c.id).where(datasets.c.project_id == project_id)
                    ).mappings()
                }
                missing_ds = [d for d in ds_ids if d not in proj_datasets]
                if missing_ds:
                    raise HTTPException(422, f"Referenced dataset not found in project: {missing_ds[0]}")
        else:
            if not project["body"]["synthetic"]:
                raise HTTPException(422, "Official laboratory cases require a separate synthetic project")
        if request.engine == "dflowfm" and request.particle_spacing_m is not None:
            raise HTTPException(422, "Particle spacing does not configure a D-Flow mesh")
        cap = capabilities(request.engine)
        if not cap["available"]:
            raise HTTPException(503, cap)
        config_hash = configuration_hash(request, cap, snap, site_config)
        # Serializes duplicate submissions for this project on both database backends.
        conn.execute(projects.update().where(projects.c.id == project_id).values(body=project["body"]))
        old = (
            conn.execute(
                select(runs).where(
                    runs.c.project_id == project_id, runs.c.idempotency_key == request.idempotency_key
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["input"]["request"] != request.model_dump(mode="json"):
                raise HTTPException(409, "Idempotency key conflicts with another request")
            return dict(old)
        ident = uid()
        body = {
            "request": request.model_dump(mode="json"),
            "capability": cap,
            "created_at": now(),
            "execution_origin": "LOCAL",
            "input_mode": "MIXED_ASSUMPTIONS" if request.case_kind == "SITE_SCENARIO" else "SYNTHETIC",
            "evidence_status": "UNASSESSED",
            "configuration_hash": config_hash,
            "case_classification": "UJJANI_APPROXIMATE_DEMONSTRATION" if request.case_kind == "SITE_SCENARIO" else ("LABORATORY_BENCHMARK" if request.engine == "dualsphysics" else "OFFICIAL_EXAMPLE"),
        }
        if snap:
            body["scenario_snapshot"] = snap
        if site_key:
            body["site_key"] = site_key
        if site_config and hasattr(site_config, "model_dump"):
            body["site_configuration"] = site_config.model_dump(mode="json")
        if ensemble_id:
            body["ensemble_id"] = ensemble_id
        cached = next(
            (row for row in conn.execute(select(runs).where(runs.c.project_id == project_id,
                runs.c.state == "SUCCEEDED")).mappings()
             if row["input"].get("configuration_hash") == config_hash and _valid_cached_source(row)),
            None,
        )
        if cached:
            result = {**cached["result"], "cached_from_run_id": cached["id"],
                      "source_run_id": cached["id"], "cache_status": "VALID_IDENTICAL_CONFIGURATION",
                      "finished_at": now()}
            conn.execute(insert(runs).values(id=ident, project_id=project_id,
                idempotency_key=request.idempotency_key, state="SUCCEEDED", input=body, result=result))
            return {"id": ident, "state": "SUCCEEDED", "input": body, "result": result}
        conn.execute(
            insert(runs).values(
                id=ident,
                project_id=project_id,
                idempotency_key=request.idempotency_key,
                state="QUEUED",
                input=body,
                result={},
            )
        )
        return {"id": ident, "state": "QUEUED", "input": body, "result": {}}


def get_runs(engine, project_id):
    with engine.connect() as conn:
        if not conn.execute(select(projects.c.id).where(projects.c.id == project_id)).first():
            raise HTTPException(404, "Project not found")
        return [dict(r) for r in conn.execute(select(runs).where(runs.c.project_id == project_id)).mappings()]


def cancel(engine, project_id, run_id):
    with engine.begin() as conn:
        changed = conn.execute(
            runs.update()
            .where(
                runs.c.id == run_id, runs.c.project_id == project_id, runs.c.state.in_(["QUEUED", "RUNNING"])
            )
            .values(state="CANCELLED")
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Run not found or already terminal")
    return {"id": run_id, "state": "CANCELLED"}
