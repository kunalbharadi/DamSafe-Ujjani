"""Single numerical worker; results succeed only after normalization validates."""

import re
import subprocess
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from ..db import engine_for, now, runs
from .adapters import ROOT, prepare_official, run_stages
from .diagnostics import native_dflow_balance
from .execution import Limits, save_json, sha256
from .products import postprocess
from .results import normalize_dflow
from .service import run_root
from .sph import assess_front_reference, normalize_sph


def finalize(engine_name, directory, case, capability):
    destination = directory / "normalized.nc"
    if engine_name == "dualsphysics":
        result = normalize_sph(directory, destination, case, capability)
        reference = (
            ROOT
            / "external/DualSPHysics/examples/main/01_DamBreak/EXP_X-DamTipPosition_Koshizula&Oka1996.txt"
        )
        result["laboratory_reference"] = assess_front_reference(directory, reference)
    else:
        native = list(directory.rglob("*_map.nc"))
        if len(native) != 1:
            raise ValueError("Expected one sequential map file; partition merge requires an explicit adapter")
        crs = case.get("physical_case", {}).get("crs", "LOCAL_CARTESIAN_OFFICIAL_F34")
        datum = case.get("physical_case", {}).get("vertical_datum", "official model bed reference")
        result = normalize_dflow(
            native[0],
            destination,
            crs=crs,
            datum=datum,
            threshold=0.01,
            source_provenance={"engine": capability, "case": case, "execution_origin": "LOCAL"},
        )
        expected = case.get("physical_case", {}).get("end_time_s")
        if expected is None or result["duration_seconds"] < expected - max(1e-6, 1e-6 * expected):
            raise ValueError("D-Flow map stopped before the documented case end time")
        history = native[0].with_name(native[0].name.replace("_map.nc", "_his.nc"))
        try:
            result["water_balance"] = native_dflow_balance(history, native[0])
        except Exception as exc:
            result["water_balance"] = {"status": "PARTIAL", "reason": str(exc)}
    result["normalized_sha256"] = sha256(destination)
    result["normalized_file"] = "normalized.nc"
    save_json(directory / "diagnostics.json", result)
    return result


def work_once(engine):
    with engine.begin() as conn:
        row = conn.execute(select(runs).where(runs.c.state == "QUEUED").limit(1)).mappings().first()
        if not row:
            return False
        claim = conn.execute(
            runs.update()
            .where(runs.c.id == row["id"], runs.c.state == "QUEUED")
            .values(state="RUNNING", result={"started_at": now()})
        )
        if claim.rowcount != 1:
            return True
    ident = row["id"]
    submission = row["input"]
    request = submission["request"]
    destination = run_root() / ident
    last_save = 0

    def cancelled():
        with engine.connect() as conn:
            return conn.execute(select(runs.c.state).where(runs.c.id == ident)).scalar() != "RUNNING"

    def progress(value):
        nonlocal last_save
        if time.monotonic() - last_save < 2:
            return
        with engine.begin() as conn:
            conn.execute(
                runs.update()
                .where(runs.c.id == ident, runs.c.state == "RUNNING")
                .values(result={"progress": value, "heartbeat_at": now()})
            )
        last_save = time.monotonic()

    try:
        if request.get("case_kind") == "SITE_SCENARIO":
            from .adapters import prepare_ujjani_site

            case = prepare_ujjani_site(destination)
        else:
            case = prepare_official(request["engine"], destination, request.get("particle_spacing_m"))
        save_json(destination / "input-manifest.json", {**submission, "case": case})
        result = run_stages(
            request["engine"],
            destination,
            ident,
            submission["capability"],
            Limits(timeout_seconds=1200, output_bytes=2_000_000_000),
            cancelled,
            progress,
        )
        if result["state"] == "SUCCEEDED" and not cancelled():
            result["normalization"] = finalize(request["engine"], destination, case, submission["capability"])
            if not cancelled():
                result["postprocessing"] = postprocess(
                    destination / "normalized.nc", destination / "products.nc", threshold_m=0.01,
                    cancelled=cancelled, progress=progress,
                )
        if cancelled():
            result["state"] = "CANCELLED"
    except Exception as e:  # noqa: BLE001 -- persist parser/engine failures, never convert to success
        result = {"state": "CANCELLED" if cancelled() else "FAILED", "error": str(e)[:2000]}
    result.update(finished_at=now(), execution_origin="LOCAL", evidence_status="UNASSESSED")
    if destination.exists():
        save_json(destination / "execution.json", {**submission, **result})
    with engine.begin() as conn:
        conn.execute(
            runs.update()
            .where(runs.c.id == ident, runs.c.state == "RUNNING")
            .values(state=result["state"], result=result)
        )
    return True


def recover_stale(engine):
    """Fail abandoned numerical leases and remove only their own containers."""
    cutoff = datetime.now(UTC) - timedelta(minutes=3)
    stale = []
    with engine.begin() as conn:
        for row in conn.execute(select(runs).where(runs.c.state == "RUNNING")).mappings():
            heartbeat = row["result"].get("heartbeat_at") or row["result"].get("started_at")
            if heartbeat and datetime.fromisoformat(heartbeat) < cutoff:
                changed = conn.execute(
                    runs.update()
                    .where(runs.c.id == row["id"], runs.c.state == "RUNNING")
                    .values(
                        state="FAILED",
                        result={
                            **row["result"],
                            "error": "Numerical worker lease expired; outputs require a new run",
                            "finished_at": now(),
                        },
                    )
                )
                if changed.rowcount:
                    stale.append(row["id"])
    for ident in stale:
        if not re.fullmatch(r"[a-f0-9-]{36}", ident):
            continue
        for stage in ("prepare", "solver", "particles"):
            try:
                subprocess.run(
                    ["docker", "rm", "-f", f"damsafe-{ident}-{stage}"],
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass  # Lease is already FAILED; a later operator can inspect Docker.
    return stale


if __name__ == "__main__":
    engine = engine_for()
    while True:
        recover_stale(engine)
        if not work_once(engine):
            time.sleep(1)
