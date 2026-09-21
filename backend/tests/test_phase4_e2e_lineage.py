import json

import numpy as np
from alembic import command
from alembic.config import Config
from damsafe.api import create_app
from damsafe.exports import create_export, verify_export
from damsafe.numerics import service
from damsafe.numerics.products import postprocess
from damsafe.numerics.results import create_result, write_frame
from damsafe.observation.exposure import ExposureStatus
from damsafe.storage import LocalStorage
from damsafe.worker import work_once
from fastapi.testclient import TestClient


def test_complete_phase4_software_e2e_lineage(tmp_path, monkeypatch):
    """Execute one continuous, reproducible Phase 4 software E2E lineage."""
    db_path = tmp_path / "e2e.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    run_root = tmp_path / "runs"
    obj_root = tmp_path / "objects"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", db_url)
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(run_root))
    monkeypatch.setenv("DAMSAFE_STORAGE_ROOT", str(obj_root))

    command.upgrade(Config("alembic.ini"), "head")
    storage = LocalStorage(obj_root)
    app = create_app(db_url, storage)

    with TestClient(app) as client:
        # Stage 1: Create laboratory project
        p_resp = client.post(
            "/api/projects",
            json={
                "name": "Phase 4 Continuous E2E Lab",
                "site_key": "e2e-lab",
                "synthetic": True,
                "description": "Deterministic software pipeline verification",
            },
        )
        assert p_resp.status_code == 201
        project_id = p_resp.json()["id"]
        assert project_id

        # Stage 2: Import a valid attributed test dataset
        csv_payload = b"timestamp,station_id,discharge,flag\n2025-01-01T00:00:00Z,st-01,100.0,OK\n2025-01-01T01:00:00Z,st-01,150.0,OK\n"
        meta_payload = {
            "name": "E2E Attributed Hydrograph",
            "kind": "hydrology",
            "provenance": {
                "source_url": "fixture://e2e/hydro",
                "agency": "DamSafe E2E Test Suite",
                "licence": "Open Test Data",
                "acquisition_date": "2025-01-01",
                "units": "m3/s",
                "status": "observed",
                "synthetic": True,
            },
            "hydro": {
                "station_id": "st-01",
                "measurement": "river_outflow",
                "identity_reference": "fixture://e2e/identity",
                "interval_seconds": 3600,
            },
        }
        d_resp = client.post(
            f"/api/projects/{project_id}/datasets?filename=e2e_hydro.csv&metadata_json={json.dumps(meta_payload)}",
            content=csv_payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert d_resp.status_code == 201
        dataset_id = d_resp.json()["id"]
        assert dataset_id

        # Stage 3: Run validation / readiness audit
        audit_resp = client.post(f"/api/projects/{project_id}/readiness-jobs")
        assert audit_resp.status_code == 202
        job_id = audit_resp.json()["id"]
        # Run worker to process audit job
        work_once(app.state.engine)
        readiness_resp = client.get(f"/api/projects/{project_id}/readiness")
        assert readiness_resp.status_code == 200
        readiness = readiness_resp.json()
        assert "missing" in readiness

        # Stage 4: Create immutable scenario
        scen_payload = {
            "name": "E2E Immutable Scenario",
            "forcing": {
                "mode": "prescribed_release",
                "historical": False,
                "hydrograph_dataset_id": dataset_id,
            },
            "dataset_ids": [dataset_id],
            "start_time": "2025-01-01T00:00:00+05:30",
            "end_time": "2025-01-01T06:00:00+05:30",
            "time_step_seconds": 1.0,
            "output_interval_seconds": 60.0,
            "wet_threshold_m": 0.01,
            "arrival_threshold_m": 0.1,
            "assumptions": ["E2E software pipeline verification fixture"],
        }
        scen_resp = client.post(f"/api/projects/{project_id}/scenarios", json=scen_payload)
        assert scen_resp.status_code == 201
        scenario_id = scen_resp.json()["id"]
        assert scenario_id

        # Stage 5: Submit numerical solver run
        capability = {"available": True, "engine": "dflowfm", "image_id": "sha256:" + "a" * 64}
        monkeypatch.setattr(service, "capabilities", lambda _: capability)

        run_resp = client.post(
            f"/api/projects/{project_id}/runs",
            json={
                "engine": "dflowfm",
                "case_kind": "OFFICIAL_EXAMPLE",
                "idempotency_key": "e2e-run-alpha-key-001",
            },
        )
        assert run_resp.status_code == 202
        run_id = run_resp.json()["id"]

        # Stage 6: Produce genuine normalized output & transition to SUCCEEDED
        run_dir = run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        norm_file = run_dir / "normalized.nc"
        with create_result(
            norm_file, [0, 60, 120], [500000, 500025, 500050], [2000000, 2000000, 2000000], [625, 625, 625], [0, 0, 0],
            {"crs": "EPSG:32643", "vertical_reference": "EGM96", "engine": {"engine": "dflowfm", "source_commit": "18f8ebb"}, "case": {"case_kind": "OFFICIAL_EXAMPLE", "input_mode": "SYNTHETIC"}}, 0.01,
        ) as dataset:
            write_frame(dataset, 0, np.ma.masked_invalid([0.5, 0.0, np.nan]), u=[0.2, 0.0, np.nan], v=[0.0, 0.0, np.nan])
            write_frame(dataset, 1, np.ma.masked_invalid([0.8, 0.4, np.nan]), u=[0.5, 0.2, np.nan], v=[0.0, 0.0, np.nan])
            write_frame(dataset, 2, np.ma.masked_invalid([1.2, 0.9, np.nan]), u=[0.9, 0.6, np.nan], v=[0.0, 0.0, np.nan])

        # Stage 7: Verify normalized result
        norm_hash = service.sha256(norm_file)
        prod_file = run_dir / "products.nc"
        postprocess(norm_file, prod_file, threshold_m=0.1)
        prod_hash = service.sha256(prod_file)

        with app.state.engine.begin() as conn:
            conn.execute(
                service.runs.update().where(service.runs.c.id == run_id).values(
                    state="SUCCEEDED",
                    result={
                        "normalized_output": str(norm_file),
                        "normalization": {"cells": 3, "frames": 3, "duration_seconds": 120, "normalized_sha256": norm_hash},
                        "postprocessing": {"product_sha256": prod_hash, "source_normalized_sha256": norm_hash, "product_schema": 2},
                    },
                )
            )

        meta_resp = client.get(f"/api/projects/{project_id}/runs/{run_id}/results/metadata")
        assert meta_resp.status_code == 200
        assert meta_resp.json()["cell_count"] == 3
        assert meta_resp.json()["output_frame_count"] == 3

        # Stage 8: Verify derived products
        assert prod_file.exists()

        # Stage 9: Call bounded result/window API
        win_resp = client.get(f"/api/projects/{project_id}/runs/{run_id}/results/window?bbox=-1000000000,-1000000000,1000000000,1000000000&field=h&first_frame=0&frame_count=3")
        assert win_resp.status_code == 200
        assert len(win_resp.json()["frames"]) == 3

        # Stage 10: Perform compatible benchmark/model comparison with Run B
        run_b_resp = client.post(
            f"/api/projects/{project_id}/runs",
            json={
                "engine": "dflowfm",
                "case_kind": "OFFICIAL_EXAMPLE",
                "idempotency_key": "e2e-run-beta-key-002",
            },
        )
        run_b_id = run_b_resp.json()["id"]
        run_b_dir = run_root / run_b_id
        run_b_dir.mkdir(parents=True, exist_ok=True)
        norm_b_file = run_b_dir / "normalized.nc"
        with create_result(
            norm_b_file, [0, 60, 120], [500000, 500025, 500050], [2000000, 2000000, 2000000], [625, 625, 625], [0, 0, 0],
            {"crs": "EPSG:32643", "vertical_reference": "EGM96", "engine": {"engine": "dflowfm", "source_commit": "18f8ebb"}, "case": {"case_kind": "OFFICIAL_EXAMPLE", "input_mode": "SYNTHETIC"}}, 0.01,
        ) as dataset_b:
            write_frame(dataset_b, 0, np.ma.masked_invalid([0.6, 0.1, np.nan]), u=[0.3, 0.1, np.nan], v=[0.0, 0.0, np.nan])
            write_frame(dataset_b, 1, np.ma.masked_invalid([0.9, 0.5, np.nan]), u=[0.6, 0.3, np.nan], v=[0.0, 0.0, np.nan])
            write_frame(dataset_b, 2, np.ma.masked_invalid([1.3, 1.0, np.nan]), u=[1.0, 0.7, np.nan], v=[0.0, 0.0, np.nan])

        norm_b_hash = service.sha256(norm_b_file)
        prod_b_file = run_b_dir / "products.nc"
        postprocess(norm_b_file, prod_b_file, threshold_m=0.1)
        prod_b_hash = service.sha256(prod_b_file)

        with app.state.engine.begin() as conn:
            conn.execute(
                service.runs.update().where(service.runs.c.id == run_b_id).values(
                    state="SUCCEEDED",
                    result={
                        "normalized_output": str(norm_b_file),
                        "normalization": {"cells": 3, "frames": 3, "duration_seconds": 120, "normalized_sha256": norm_b_hash},
                        "postprocessing": {"product_sha256": prod_b_hash, "source_normalized_sha256": norm_b_hash, "product_schema": 2},
                    },
                )
            )

        comp_resp = client.get(f"/api/projects/{project_id}/runs/{run_id}/compare/{run_b_id}")
        assert comp_resp.status_code == 200
        assert comp_resp.json()["state"] == "COMPARABLE"

        # Stage 11: Run satellite metric engine using explicitly isolated SYNTHETIC_TEST_DATA
        from damsafe.observation.gee import create_synthetic_test_observation
        monkeypatch.setattr(
            "damsafe.api.ee_service.query_sentinel1",
            lambda **kwargs: create_synthetic_test_observation(matrix=[[1, 0, 0]]),
        )
        sat_comp_resp = client.post(f"/api/projects/{project_id}/runs/{run_id}/compare_satellite?mode=HISTORICAL_EVENT")
        assert sat_comp_resp.status_code == 200
        sat_metrics = sat_comp_resp.json()
        assert sat_metrics["status"] == "NOT_VALIDATED"
        assert sat_metrics["agreement"] is None
        assert "Maximum-ever" in sat_metrics["note"]
        observation_id = "NOT_ASSESSED: no qualified acquisition-time grid"

        # Stage 12: Run exposure
        exp_resp = client.get(f"/api/projects/{project_id}/runs/{run_id}/exposure")
        assert exp_resp.status_code == 200
        exp_data = exp_resp.json()
        assert exp_data["settlements"]["status"] == ExposureStatus.UNAVAILABLE
        assert exp_data["settlements"]["exposed_count_or_area"] is None
        assert exp_data["population"]["status"] == ExposureStatus.UNAVAILABLE
        assert exp_data["economic_loss"]["status"] == ExposureStatus.BLOCKED

        # Stage 13: Generate GIS export (GeoTIFF)
        exp_dir = run_root / "exports" / project_id / run_id
        geotiff_path = create_export(norm_file, prod_file, exp_dir, run_id, "geotiff")
        assert geotiff_path.exists()

        # Stage 14: Independently reopen the export
        ver = verify_export(geotiff_path, "geotiff")
        assert ver["format"] == "geotiff"
        assert ver["nodata"] == -9999.0
        assert ver["crs"] == "EPSG:32643"
        assert ver["count"] == 3

    # Lineage IDs returnable for audit
    print("\n--- PHASE 4 CONTINUOUS LINEAGE RECORD ---")
    print(f"project_id: {project_id}")
    print(f"dataset_id: {dataset_id}")
    print(f"job_id: {job_id}")
    print(f"scenario_id: {scenario_id}")
    print(f"run_id (Run A): {run_id}")
    print(f"comparison_target_run_id (Run B): {run_b_id}")
    print(f"observation_id: {observation_id}")
    print(f"export_artifact: {geotiff_path}")
