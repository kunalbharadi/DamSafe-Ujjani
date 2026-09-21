import json
from pathlib import Path
from uuid import uuid4

import netCDF4
import numpy as np
import pytest
import rasterio
from damsafe.contracts import RunRequest
from damsafe.db import engine_for, metadata, projects, scenarios
from damsafe.exports import create_export, verify_export
from damsafe.numerics.adapters import capabilities
from damsafe.numerics.products import metadata as product_metadata
from damsafe.numerics.service import get_runs, result_record, run_root, submit
from damsafe.numerics.worker import work_once
from sqlalchemy import insert, select


@pytest.mark.skipif(not capabilities("dflowfm")["available"], reason="DFlow-FM docker container not available in test environment")
def test_persistent_ujjani_site_run_lifecycle_and_exports(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(tmp_path / "runs"))
    db_path = tmp_path / "damsafe_test.db"
    engine = engine_for(f"sqlite:///{db_path}")
    metadata.create_all(engine)

    project_id = str(uuid4())
    scenario_id = str(uuid4())

    # 1. Create site project in DB
    proj_body = {
        "id": project_id,
        "name": "Ujjani Bhima Flood Simulation Project",
        "site_key": "ujjani-bhima",
        "synthetic": False,
        "description": "Hydrodynamic demonstration project for Ujjani Dam to Pandharpur reach.",
        "verified_bounds_wgs84": [74.60, 17.65, 75.95, 18.35],
        "computation_crs": "EPSG:32643",
        "vertical_reference": "EGM96",
        "source_url": "https://wrd.maharashtra.gov.in/",
    }
    with engine.begin() as conn:
        conn.execute(insert(projects).values(id=project_id, body=proj_body))

    # 2. Create immutable scenario in DB
    scen_snapshot = {
        "project": proj_body,
        "datasets": [],
        "scenario": {
            "name": "October 2020 Bhima Flood Approximate Run",
            "forcing": {"mode": "prescribed_release", "historical": True},
            "start_time": "2020-10-14T00:00:00Z",
            "end_time": "2020-10-22T23:59:59Z",
            "time_step_seconds": 30.0,
            "output_interval_seconds": 3600.0,
            "wet_threshold_m": 0.01,
            "arrival_threshold_m": 0.05,
        },
    }
    with engine.begin() as conn:
        conn.execute(
            insert(scenarios).values(
                id=scenario_id,
                project_id=project_id,
                body={"id": scenario_id, "snapshot": scen_snapshot},
            )
        )

    # 3. Submit SITE_SCENARIO run
    req = RunRequest(
        engine="dflowfm",
        case_kind="SITE_SCENARIO",
        scenario_id=scenario_id,
        idempotency_key="ujjani-run-oct2020-001",
    )
    queued = submit(engine, project_id, req)
    run_id = queued["id"]
    assert queued["state"] == "QUEUED"
    assert queued["input"]["case_classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"
    assert queued["input"]["input_mode"] == "MIXED_ASSUMPTIONS"
    assert queued["input"]["configuration_hash"]

    # 4. Worker executes run
    worked = work_once(engine)
    assert worked is True

    # 5. Verify run SUCCEEDED in database
    run_row, _source_row, norm_path = result_record(engine, project_id, run_id)
    assert run_row["state"] == "SUCCEEDED"
    assert run_row["id"] == run_id
    assert run_row["input"]["case_classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"

    # 6. Verify native solver artifacts
    run_dir = run_root() / run_id
    assert (run_dir / "solver.log").is_file()
    assert (run_dir / "dimr_config.xml").is_file()
    assert (run_dir / "dflowfm/ujjani_bhima.mdu").is_file()
    assert (run_dir / "dflowfm/ujjani_net.nc").is_file()
    assert (run_dir / "dflowfm/upstream_discharge.bc").is_file()
    assert (run_dir / "dflowfm/downstream_stage.bc").is_file()
    assert (run_dir / "dflowfm/DFM_OUTPUT_ujjani_bhima/ujjani_bhima_map.nc").is_file()

    # 7. Verify normalized NetCDF
    assert norm_path.is_file()
    with netCDF4.Dataset(norm_path) as ds:
        times = ds["time"][:]
        assert len(times) == 217
        assert times[-1] == 777600.0  # 9 days
        assert len(ds.dimensions["cell"]) == 80

        h = ds["h"][:]
        ds["u"][:]
        ds["v"][:]
        valid = ds["valid"][:]
        ds["wet"][:]

        # Numerical sanity
        assert not np.isnan(h[valid == 1]).any()
        assert not np.isinf(h[valid == 1]).any()
        assert not (h[valid == 1] < 0).any()
        assert np.min(h[valid == 1]) >= 0

        # Provenance check
        prov = json.loads(ds.provenance_json)
        assert prov["crs"] == "EPSG:32643"
        assert prov["vertical_reference"] == "EGM96"
        assert prov["case"]["classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"

    # 8. Verify postprocessed products
    prod_path = run_dir / "products.nc"
    assert prod_path.is_file()
    with netCDF4.Dataset(prod_path) as pds:
        assert pds.schema_version == 2
        max_h = pds["maximum_depth_m"][:]
        pds["maximum_velocity_m_s"][:]
        duration = pds["flood_duration_s"][:]
        pds["arrival_elapsed_s"][:]

        assert not np.isnan(max_h).all()
        assert np.nanmin(max_h) >= 0.0
        assert np.nanmax(max_h) > 5.0  # deep channel reaches
        assert np.nanmin(duration) >= 0.0

    # 9. Verify product metadata
    meta = product_metadata(
        norm_path,
        run_id=run_id,
        scenario_id=scenario_id,
        configuration_hash=run_row["input"]["configuration_hash"],
    )
    assert meta["run_id"] == run_id
    assert meta["scenario_id"] == scenario_id
    assert meta["crs"] == "EPSG:32643"
    assert meta["vertical_datum"] == "EGM96"
    assert meta["cell_count"] == 80
    assert meta["output_frame_count"] == 217

    # 10. Generate and independently reopen exports
    export_dir = tmp_path / "exports"
    for fmt in ("geotiff", "geojson", "csv", "shapefile", "kml", "html"):
        out_file = create_export(norm_path, prod_path, export_dir, run_id, fmt, meta)
        assert out_file.is_file()
        verification = verify_export(out_file, fmt)
        assert verification["format"] == fmt

    # Inspect GeoTIFF
    gtiff_path = export_dir / f"{run_id}-geotiff.tif"
    with rasterio.open(gtiff_path) as src:
        assert src.crs.to_string() == "EPSG:32643"
        assert src.nodata == -9999.0
        assert src.width > 1
        assert src.height > 1
        assert src.tags().get("damsafe_units") == "metres"

    # 11. Test restart persistence
    # Create new database engine pointing to existing SQLite file
    engine2 = engine_for(f"sqlite:///{db_path}")
    with engine2.connect() as conn:
        proj_row = conn.execute(select(projects).where(projects.c.id == project_id)).mappings().first()
        assert proj_row["id"] == project_id
        scen_row = conn.execute(select(scenarios).where(scenarios.c.id == scenario_id)).mappings().first()
        assert scen_row["id"] == scenario_id

    all_runs = get_runs(engine2, project_id)
    assert len(all_runs) == 1
    assert all_runs[0]["id"] == run_id
    assert all_runs[0]["state"] == "SUCCEEDED"
    assert all_runs[0]["input"]["case_classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"

    # Verify result record is still accessible
    _r_row, _s_row, reloaded_norm_path = result_record(engine2, project_id, run_id)
    assert reloaded_norm_path.is_file()
