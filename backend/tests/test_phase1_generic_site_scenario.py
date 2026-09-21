"""Tests for Phase 1: Generic Site Architecture + Real SITE_SCENARIO Execution."""

import netCDF4
import numpy as np
import pytest
from damsafe.contracts import RunRequest
from damsafe.db import metadata, projects, runs, scenarios
from damsafe.numerics import service as run_service
from damsafe.numerics import worker as run_worker
from damsafe.numerics.adapters import capabilities
from damsafe.site.case_builder import build_site_case
from damsafe.site.configuration import (
    SiteSpatial,
    get_ujjani_site_configuration,
)
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select


def test_site_configuration_validation():
    # 1. Valid Ujjani preset
    site = get_ujjani_site_configuration()
    assert site.identity.site_key == "ujjani-bhima"
    assert site.spatial.computation_crs == "EPSG:32643"
    assert len(site.spatial.river_centerline_wgs84) >= 2
    assert site.structure.dam_height_m == 56.4
    assert site.structure.gross_storage_capacity_m3 == 3_140_000_000.0

    # 2. Invalid bounds rejected
    with pytest.raises(ValidationError, match="bounding box"):
        SiteSpatial(
            bounds_wgs84=(200.0, 17.0, 75.0, 18.0),
            computation_crs="EPSG:32643",
            river_centerline_wgs84=((75.0, 18.0), (75.5, 17.5)),
        )

    # 3. Centerline with < 2 points rejected
    with pytest.raises(ValidationError, match="at least 2 points"):
        SiteSpatial(
            bounds_wgs84=(74.0, 17.0, 76.0, 18.5),
            computation_crs="EPSG:32643",
            river_centerline_wgs84=((75.0, 18.0),),
        )


def test_site_case_builder_generates_all_solver_inputs(tmp_path):
    target = tmp_path / "generic_case_dir"
    site = get_ujjani_site_configuration()
    snapshot = {
        "scenario": {
            "name": "Phase 1 Demonstration Breach",
            "scenario_type": "DAM_BREACH",
            "start_time": "2020-10-14T00:00:00Z",
            "end_time": "2020-10-22T23:59:59Z",
            "output_interval_seconds": 3600.0,
            "roughness": {"manning": 0.038},
            "downstream_boundary": {"stage_m": 443.5},
        },
        "project": {"site_key": "ujjani-bhima", "name": "Ujjani Demo"},
    }

    case = build_site_case(site, snapshot, target)

    assert case["case_kind"] == "SITE_SCENARIO"
    assert case["scenario_type"] == "DAM_BREACH"
    assert case["site_key"] == "ujjani-bhima"
    assert (target / "dimr_config.xml").is_file()
    assert (target / "manifest.json").is_file()

    dflowfm = target / "dflowfm"
    assert (dflowfm / "ujjani_bhima.mdu").is_file()
    assert (dflowfm / "ujjani_bhima.ext").is_file()
    assert (dflowfm / "upstream_discharge.bc").is_file()
    assert (dflowfm / "downstream_stage.bc").is_file()
    assert (dflowfm / "initial_water_level.xyz").is_file()
    assert (dflowfm / "ujjani_init.ext").is_file()
    assert (dflowfm / "ujjani_net.nc").is_file()

    # Verify custom roughness and downstream stage reached solver files
    mdu_text = (dflowfm / "ujjani_bhima.mdu").read_text(encoding="utf-8")
    assert "0.0380" in mdu_text

    down_bc = (dflowfm / "downstream_stage.bc").read_text(encoding="utf-8")
    assert "443.50" in down_bc


def test_scenario_sensitivity_configuration_hashes_differ():
    cap = {"available": True, "image_id": "sha256:d439312899ce18fc3c498355b3c87ddda55a59b3b74e762bc2b08425b2980cd8"}
    req_a = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id="scen-controlled-release-01",
        idempotency_key="idemp-key-001",
    )
    req_b = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id="scen-dam-breach-02",
        idempotency_key="idemp-key-002",
    )

    site = get_ujjani_site_configuration()
    snap_a = {
        "scenario": {
            "name": "Controlled Release 250k cusecs",
            "scenario_type": "CONTROLLED_RELEASE",
            "start_time": "2020-10-14T00:00:00Z",
            "end_time": "2020-10-22T23:59:59Z",
            "roughness": {"manning": 0.035},
        }
    }
    snap_b = {
        "scenario": {
            "name": "Dam Breach Scenario",
            "scenario_type": "DAM_BREACH",
            "start_time": "2020-10-14T00:00:00Z",
            "end_time": "2020-10-22T23:59:59Z",
            "roughness": {"manning": 0.045},
        }
    }

    hash_a = run_service.configuration_hash(req_a, cap, snap_a, site)
    hash_b = run_service.configuration_hash(req_b, cap, snap_b, site)

    assert hash_a != hash_b
    assert len(hash_a) == 64
    assert len(hash_b) == 64


def test_site_scenario_validation_rejects_missing_scenario(tmp_path):
    db_file = tmp_path / "test_val.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(projects.insert().values(
            id="proj-val",
            body={"id": "proj-val", "name": "Val Project", "site_key": "ujjani-bhima", "synthetic": False},
        ))

    req = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id="non-existent-scenario",
        idempotency_key="val-req-001",
    )

    with pytest.raises(HTTPException) as exc:
        run_service.submit(engine, "proj-val", req)
    assert exc.value.status_code == 422
    assert "Select an immutable scenario" in str(exc.value.detail)


@pytest.mark.skipif(not capabilities("dflowfm")["available"], reason="D-Flow FM docker image not available")
def test_real_site_scenario_end_to_end_dflow_execution(tmp_path, monkeypatch):
    """Golden Integration Test: UI scenario -> Snapshot -> SITE_SCENARIO -> D-Flow FM -> SUCCEEDED -> normalized.nc & products.nc"""
    db_file = tmp_path / "test_golden.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    metadata.create_all(engine)

    run_root_dir = tmp_path / "runs"
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(run_root_dir))

    proj_id = "golden-ujjani-proj"
    scen_id = "golden-breach-scen"

    # 1. Project & Scenario Snapshot
    snapshot = {
        "project": {"id": proj_id, "name": "Ujjani Flagship", "site_key": "ujjani-bhima", "synthetic": False},
        "scenario": {
            "name": "Ujjani Dam Breach Demonstration",
            "scenario_type": "DAM_BREACH",
            "start_time": "2020-10-14T00:00:00Z",
            "end_time": "2020-10-22T23:59:59Z",
            "output_interval_seconds": 3600.0,
            "roughness": {"manning": 0.035},
            "downstream_boundary": {"stage_m": 443.2},
        },
    }

    with engine.begin() as conn:
        conn.execute(projects.insert().values(
            id=proj_id,
            body={"id": proj_id, "name": "Ujjani Flagship", "site_key": "ujjani-bhima", "synthetic": False},
        ))
        conn.execute(scenarios.insert().values(
            id=scen_id,
            project_id=proj_id,
            body={
                "id": scen_id,
                "project_id": proj_id,
                "name": "Ujjani Dam Breach Demonstration",
                "snapshot": snapshot,
            },
        ))

    # 2. Submit SITE_SCENARIO
    req = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id=scen_id,
        idempotency_key="golden-run-001",
    )

    rec = run_service.submit(engine, proj_id, req)
    run_id = rec["id"]
    assert rec["state"] == "QUEUED"
    assert rec["input"]["request"]["case_kind"] == "SITE_SCENARIO"
    assert rec["input"]["case_classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"

    # 3. Worker executes generic case builder and runs D-Flow FM in Docker
    worked = run_worker.work_once(engine)
    assert worked is True

    # 4. Verify terminal status in DB
    with engine.connect() as conn:
        row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
        if row["state"] != "SUCCEEDED":
            print("FAILURE DETAIL:", row["result"])
            log_path = run_root_dir / run_id / "solver.log"
            if log_path.is_file():
                print("SOLVER LOG:\n", log_path.read_text(encoding="utf-8", errors="replace"))
        assert row["state"] == "SUCCEEDED"

    # 5. Verify generated files
    run_dir = run_root_dir / run_id
    assert (run_dir / "normalized.nc").is_file()
    assert (run_dir / "products.nc").is_file()
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "solver.log").is_file()

    # 6. Verify non-zero physical depth and velocity in products.nc
    with netCDF4.Dataset(run_dir / "products.nc", "r") as pds:
        assert "maximum_depth_m" in pds.variables
        assert "maximum_velocity_m_s" in pds.variables
        assert "arrival_elapsed_s" in pds.variables
        max_d = pds.variables["maximum_depth_m"][:]
        max_v = pds.variables["maximum_velocity_m_s"][:]
        assert np.max(max_d) > 1.0
        assert np.all(np.isfinite(max_d))
        assert np.max(max_v) > 0.1
