import json
from pathlib import Path
import netCDF4
import numpy as np
import pytest
from sqlalchemy import create_engine, select

from damsafe.db import metadata, runs, projects, scenarios
from damsafe.contracts import RunRequest
from damsafe.exports import create_export, verify_export
from damsafe.numerics import service as run_service, worker as run_worker
from damsafe.site.hydraulic_case import (
    UjjaniApproximateCaseConfig,
    build_ujjani_approximate_case,
    _build_curvilinear_reach_netcdf,
    generate_oct2020_hydrograph,
)


def test_boundary_connectivity_and_mdu_keywords(tmp_path):
    config = UjjaniApproximateCaseConfig()
    case_dict = build_ujjani_approximate_case(tmp_path, config)
    
    dflowfm_dir = tmp_path / "dflowfm"
    mdu_content = (dflowfm_dir / "ujjani_bhima.mdu").read_text(encoding="utf-8")
    assert "ExtForceFileNew                   = ujjani_bhima.ext" in mdu_content
    assert "IniFieldFile                      = ujjani_init.ext" in mdu_content
    assert "BathymetryFile" not in mdu_content
    
    # Check NetCDF mesh boundary links
    with netCDF4.Dataset(dflowfm_dir / "ujjani_net.nc") as ds:
        bnd_links = ds.variables["BndLink"][:]
        assert len(bnd_links) == 48  # 2*(20+4) for 20x4 mesh
        assert np.all(bnd_links > 0)
        
    # Check PLI and BC naming alignment
    up_pli = (dflowfm_dir / "upstream_discharge.pli").read_text(encoding="utf-8")
    assert "UpstreamDischarge_0001" in up_pli
    assert "UpstreamDischarge_0002" in up_pli
    
    up_bc = (dflowfm_dir / "upstream_discharge.bc").read_text(encoding="utf-8")
    assert "name                  = UpstreamDischarge_0001" in up_bc
    assert "name                  = UpstreamDischarge_0002" in up_bc
    assert "unit                  = minutes since 2020-10-14 00:00:00 +00:00" in up_bc
    assert "quantity              = dischargebnd" in up_bc
    
    # Check initial water level XYZ
    init_xyz = (dflowfm_dir / "initial_water_level.xyz").read_text(encoding="utf-8")
    assert len(init_xyz.strip().splitlines()) == 105  # (20+1)*(4+1)


def test_2d_geotiff_rasterization(tmp_path):
    from damsafe.numerics.results import create_result, write_frame
    from damsafe.numerics.products import postprocess

    source = tmp_path / "normalized.nc"
    product = tmp_path / "products.nc"
    
    # Create 2D point cloud representing Ujjani reach
    x = np.linspace(512000, 534000, 20)
    y = np.linspace(1998000, 1956000, 20)
    xx, yy = [], []
    for px, py in zip(x, y):
        for offset in [-100, 100]:
            xx.append(px + offset)
            yy.append(py)
    xx = np.array(xx, dtype=float)
    yy = np.array(yy, dtype=float)
    n_cells = len(xx)
    
    with create_result(
        source,
        [0, 3600],
        xx.tolist(),
        yy.tolist(),
        [1000.0] * n_cells,
        [0.0] * n_cells,
        {"crs": "EPSG:32643", "engine": {"engine": "dflowfm"}, "case": {"case_kind": "SITE_SCENARIO"}},
        0.01,
    ) as ds:
        write_frame(ds, 0, np.full(n_cells, 2.5), u=np.full(n_cells, 1.2), v=np.full(n_cells, 0.0))
        write_frame(ds, 1, np.full(n_cells, 6.8), u=np.full(n_cells, 2.4), v=np.full(n_cells, 0.0))
        
    postprocess(source, product, threshold_m=0.01)
    
    exp_dir = tmp_path / "exports"
    gtiff = create_export(source, product, exp_dir, "test-2d-run", "geotiff")
    info = verify_export(gtiff, "geotiff")
    
    assert info["height"] > 1
    assert info["width"] > 1
    assert info["coordinate_convention"] == "2D_INUNDATION_RASTER"
    assert info["nodata"] == -9999.0
    assert info["crs"] == "EPSG:32643"


def test_persistent_dynamic_site_run_lifecycle(tmp_path, monkeypatch):
    db_file = tmp_path / "test_dyn.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url)
    metadata.create_all(engine)
    
    run_root_dir = tmp_path / "runs"
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(run_root_dir))
    
    proj_id = "test-dyn-proj"
    scen_id = "test-dyn-scen"
    
    with engine.begin() as conn:
        conn.execute(projects.insert().values(
            id=proj_id,
            body={"id": proj_id, "name": "Dynamic Demo", "site_key": "ujjani-bhima", "synthetic": False},
        ))
        conn.execute(scenarios.insert().values(
            id=scen_id,
            project_id=proj_id,
            body={
                "id": scen_id,
                "project_id": proj_id,
                "snapshot": {
                    "case_kind": "SITE_SCENARIO",
                    "case_id": "ujjani_bhima_oct2020",
                    "classification": "UJJANI_APPROXIMATE_DEMONSTRATION",
                },
            },
        ))
        
    req = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id=scen_id,
        idempotency_key="test-dyn-req-001",
    )
    rec = run_service.submit(engine, proj_id, req)
    run_id = rec["id"]
    assert rec["state"] == "QUEUED"
    assert rec["input"]["case_classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"
    
    # Process job
    worked = run_worker.work_once(engine)
    assert worked is True
    
    # Check DB state
    with engine.connect() as conn:
        row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
        assert row["state"] == "SUCCEEDED"
        
    run_dir = run_root_dir / run_id
    assert (run_dir / "normalized.nc").is_file()
    assert (run_dir / "products.nc").is_file()
    
    # Verify non-trivial velocities and depths in normalized output
    with netCDF4.Dataset(run_dir / "normalized.nc") as ds:
        assert len(ds.variables["time"]) == 217
        h = ds.variables["h"][:]
        u = ds.variables["u"][:]
        v = ds.variables["v"][:]
        vel = np.hypot(u, v)
        assert np.max(h) > 5.0
        assert np.max(vel) > 1.0  # Dynamic velocities proven!
        assert np.all(np.isfinite(h[0, :]))
