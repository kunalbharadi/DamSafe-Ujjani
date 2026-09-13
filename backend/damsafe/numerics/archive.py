"""Register only checksum-pinned, locally retained Phase 2 solver evidence."""

import json
import os
from pathlib import Path

import netCDF4
from sqlalchemy import insert, select

from ..db import projects, runs, uid
from .execution import sha256
from .products import PRODUCT_SCHEMA, postprocess
from .service import run_root

ROOT = Path(__file__).resolve().parents[3]
ARCHIVES = {
    "5f337ace-316f-487b-8962-330e97a11685": (
        "dflowfm", "845add7a372f0b2496dd1406cfeab46cfa7778265c98f944b5942534010a86cd"
    ),
    "7eac17d0-15d0-4113-91b1-8f3461329a5c": (
        "dualsphysics", "da19dce680cf54725c235b5058d3da65d086cc7a1a6c7d3fa07367269c98f97f"
    ),
}
EVIDENCE_NAMES = {
    "5f337ace-316f-487b-8962-330e97a11685": "dflowfm-shared",
    "7eac17d0-15d0-4113-91b1-8f3461329a5c": "dualsphysics",
}


def _product_record(source: Path, destination: Path):
    if destination.is_file():
        try:
            with netCDF4.Dataset(destination) as ds:
                if (getattr(ds, "schema_version", None) == PRODUCT_SCHEMA
                        and ds.source_normalized_sha256 == sha256(source)):
                    return {"product_file": destination.name, "product_sha256": sha256(destination),
                            "source_normalized_sha256": sha256(source),
                            "arrival_threshold_m": float(ds.arrival_threshold_m),
                            "status": "COMPUTED_FROM_SAVED_NUMERICAL_OUTPUT"}
        except (OSError, AttributeError):
            pass
    candidate = destination.with_name("products-v2-pending.nc")
    if candidate.exists():
        raise ValueError("Prior incomplete product reprocessing requires operator review")
    report = postprocess(source, candidate, threshold_m=.01)
    os.replace(candidate, destination)
    return {**report, "product_file": destination.name, "product_sha256": sha256(destination)}


def register(engine):
    """Idempotent archive registration; never claims a newly executed solver run."""
    available = []
    for ident, (name, expected) in ARCHIVES.items():
        source = run_root() / ident / "normalized.nc"
        evidence = ROOT / "docs/evidence/phase2" / f"{EVIDENCE_NAMES[ident]}-{ident}.json"
        if not source.is_file() or not evidence.is_file():
            continue
        if sha256(source) != expected:
            raise ValueError(f"Pinned Phase 2 output checksum mismatch: {ident}")
        manifest = json.loads(evidence.read_text(encoding="utf-8"))
        if manifest.get("id") != ident or manifest.get("state") != "SUCCEEDED" or manifest.get("engine", {}).get("engine") != name:
            raise ValueError(f"Phase 2 evidence identity/state mismatch: {ident}")
        product = _product_record(source, source.with_name("products.nc"))
        available.append((ident, name, expected, manifest, product))
    if not available:
        return {"project_id": None, "registered": [], "note": "No pinned local Phase 2 outputs were available"}
    with engine.begin() as conn:
        project = next((row for row in conn.execute(select(projects)).mappings()
                        if row["body"].get("site_key") == "laboratory-examples"), None)
        if project and not project["body"].get("synthetic"):
            raise ValueError("Laboratory project key belongs to a non-synthetic project")
        if not project:
            project_id = uid()
            body = {"name": "DamSafe laboratory examples", "site_key": "laboratory-examples",
                    "synthetic": True, "description": "Archived Phase 2 solver evidence; never Ujjani",
                    "verified_bounds_wgs84": None, "computation_crs": None, "vertical_reference": None,
                    "source_url": None}
            conn.execute(insert(projects).values(id=project_id, body=body))
        else:
            project_id = project["id"]
        registered = []
        for ident, name, checksum, manifest, product in available:
            existing = conn.execute(select(runs).where(runs.c.id == ident)).mappings().first()
            if existing:
                if existing["project_id"] != project_id or existing["result"].get("normalization", {}).get("normalized_sha256") != checksum:
                    raise ValueError(f"Existing run ID conflicts with pinned archive: {ident}")
                registered.append(ident)
                continue
            config_hash = sha256(ROOT / "docs/evidence/phase2" / f"{EVIDENCE_NAMES[ident]}-{ident}.json")
            conn.execute(insert(runs).values(id=ident, project_id=project_id,
                idempotency_key=f"phase2-archive-{ident}", state="SUCCEEDED",
                input={"request": {"engine": name, "case_kind": manifest["case"]["case_kind"], "scenario_id": None},
                       "configuration_hash": config_hash, "input_mode": "SYNTHETIC",
                       "execution_origin": "ARCHIVED_LOCAL_PHASE2", "evidence_status": manifest.get("evidence_status", "UNASSESSED")},
                result={"normalization": {"normalized_sha256": checksum,
                                          "frames": manifest.get("normalization", {}).get("frames"),
                                          "cells": manifest.get("normalization", {}).get("cells")},
                        "postprocessing": product, "stages": manifest.get("stages", []),
                        "archive_registration": True, "source_run_id": ident,
                        "evidence_status": manifest.get("evidence_status", "UNASSESSED")}))
            registered.append(ident)
    return {"project_id": project_id, "registered": registered,
            "note": "Registered retained solver outputs; no solver was executed by registration"}
