import json

import numpy as np
from alembic import command
from alembic.config import Config
from damsafe.api import create_app
from damsafe.exports import create_export, verify_export
from damsafe.numerics import service
from damsafe.numerics.products import postprocess
from damsafe.numerics.results import create_result, write_frame
from damsafe.storage import LocalStorage
from fastapi.testclient import TestClient


def test_exports_are_reopenable_and_preserve_nodata(tmp_path):
    source = tmp_path / "normalized.nc"
    product = tmp_path / "products.nc"
    with create_result(
        source, [0, 1], [500000, 500001], [2000000, 2000001], [1, 1], [0, 0],
        {"crs": "EPSG:32643", "engine": {"engine": "fixture"}, "case": {"case_kind": "OFFICIAL_EXAMPLE"}}, .1,
    ) as dataset:
        write_frame(dataset, 0, np.ma.masked_invalid([.2, np.nan]), u=[1, 0], v=[0, 0])
        write_frame(dataset, 1, np.ma.masked_invalid([.3, np.nan]), u=[2, 0], v=[0, 0])
    postprocess(source, product, threshold_m=.1)
    output = tmp_path / "exports"
    geojson = create_export(source, product, output, "run/unsafe", "geojson")
    body = json.loads(geojson.read_text(encoding="utf-8"))
    assert len(body["features"]) == 2
    assert body["features"][1]["properties"]["maximum_depth_m"] is None
    assert verify_export(geojson, "geojson")["feature_count"] == 2
    geotiff = create_export(source, product, output, "run-safe", "geotiff")
    assert verify_export(geotiff, "geotiff")["nodata"] == -9999.0
    archive = create_export(source, product, output, "run-safe", "shapefile")
    checked = verify_export(archive, "shapefile")
    assert checked["complete"] is True
    csv_path = create_export(source, product, output, "run-safe", "csv")
    assert "NODATA" in csv_path.read_text(encoding="utf-8")


def test_ensemble_preserves_variant_identity_and_changes_require_new_runs(tmp_path, monkeypatch):
    database = f"sqlite:///{(tmp_path / 'ensemble.db').as_posix()}"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", database)
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(tmp_path / "runs"))
    command.upgrade(Config("alembic.ini"), "head")
    capability = {"available": True, "engine": "dualsphysics", "image_id": "sha256:" + "b" * 64}
    monkeypatch.setattr(service, "capabilities", lambda _: capability)
    app = create_app(database, LocalStorage(tmp_path / "objects"))
    with TestClient(app) as client:
        project = client.post("/api/projects", json={
            "name": "Ensemble lab", "site_key": "ensemble-lab", "synthetic": True,
        }).json()["id"]
        response = client.post(f"/api/projects/{project}/ensembles", json={
            "name": "Spacing sensitivity",
            "variants": [
                {"engine": "dualsphysics", "case_kind": "OFFICIAL_EXAMPLE",
                 "idempotency_key": "ens-a-001", "particle_spacing_m": .01},
                {"engine": "dualsphysics", "case_kind": "OFFICIAL_EXAMPLE",
                 "idempotency_key": "ens-b-002", "particle_spacing_m": .02},
            ],
        })
        assert response.status_code == 202, response.text
        record = response.json()
        assert len(record["run_ids"]) == 2
        runs = client.get(f"/api/projects/{project}/runs").json()
        assert {run["input"]["request"]["particle_spacing_m"] for run in runs} == {.01, .02}
        assert len({run["input"]["configuration_hash"] for run in runs}) == 2
