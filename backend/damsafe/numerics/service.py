import os
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import insert, select

from ..contracts import RunRequest, ScenarioInput
from ..db import now, projects, runs, scenarios, uid
from ..readiness import assess
from .adapters import capabilities


def run_root():
    path = Path(os.environ.get("DAMSAFE_RUN_ROOT", ".local/runs")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def submit(engine, project_id, request: RunRequest):
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
            check = assess(snap["project"], snap["datasets"], ScenarioInput.model_validate(snap["scenario"]))
            raise HTTPException(
                422,
                {"message": "Site mesh, boundaries and physical inputs are not verified", "readiness": check},
            )
        if not project["body"]["synthetic"]:
            raise HTTPException(422, "Official laboratory cases require a separate synthetic project")
        if request.engine == "dflowfm" and request.particle_spacing_m is not None:
            raise HTTPException(422, "Particle spacing does not configure a D-Flow mesh")
        cap = capabilities(request.engine)
        if not cap["available"]:
            raise HTTPException(503, cap)
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
            "input_mode": "SYNTHETIC",
            "evidence_status": "UNASSESSED",
        }
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
