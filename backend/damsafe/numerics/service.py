import hashlib
import json
import os
from pathlib import Path

import netCDF4
from fastapi import HTTPException
from sqlalchemy import insert, select

from ..contracts import RunRequest
from ..db import now, projects, runs, scenarios, uid
from .adapters import ROOT, SOURCES, capabilities
from .execution import sha256
from .products import PRODUCT_SCHEMA


def configuration_hash(request: RunRequest, capability: dict, snapshot: dict | None = None):
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
            # The current site worker calls prepare_ujjani_site() with defaults.
            # Do not claim that an arbitrary immutable scenario was executed.
            raise HTTPException(
                422,
                "Custom site execution is blocked until the worker binds the saved scenario's "
                "forcing, datasets, boundaries and time settings. Retained site demonstrations "
                "remain available for viewing and export; laboratory runs remain supported.",
            )
        else:
            if not project["body"]["synthetic"]:
                raise HTTPException(422, "Official laboratory cases require a separate synthetic project")
        if request.engine == "dflowfm" and request.particle_spacing_m is not None:
            raise HTTPException(422, "Particle spacing does not configure a D-Flow mesh")
        cap = capabilities(request.engine)
        if not cap["available"]:
            raise HTTPException(503, cap)
        config_hash = configuration_hash(request, cap, snap)
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
