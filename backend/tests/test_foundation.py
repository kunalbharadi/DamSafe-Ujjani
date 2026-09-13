import json

import numpy as np
import pytest
import rasterio
from alembic import command
from alembic.config import Config
from damsafe.api import create_app
from damsafe.contracts import DatasetInput, ScenarioInput
from damsafe.ingestion import read_hydrology, read_terrain
from damsafe.readiness import assess
from damsafe.storage import LocalStorage
from damsafe.worker import work_once
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def env(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path.as_posix()}/test.db"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(url, LocalStorage(tmp_path / "objects"))
    with TestClient(app) as client:
        yield client, app, url, tmp_path


def project(client, synthetic=True):
    r = client.post(
        "/api/projects",
        json={"name": "Synthetic laboratory fixture", "site_key": "test", "synthetic": synthetic},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def spec(**hydro):
    return {
        "name": "Software fixture discharge",
        "kind": "hydrology",
        "provenance": {
            "source_url": "fixture://tests",
            "agency": "Software tests",
            "licence": "Test fixture",
            "acquisition_date": "2025-01-01",
            "units": "m3/s",
            "status": "assumed",
            "synthetic": True,
        },
        "hydro": {
            "station_id": "fixture",
            "measurement": "river_outflow",
            "identity_reference": "fixture://contract",
            **hydro,
        },
    }


GOOD = b"timestamp,station_id,discharge,flag\n2025-01-01T00:00:00Z,fixture,1,OK\n2025-01-01T01:00:00Z,fixture,2,OK\n"


def upload(client, pid, content=GOOD, name="flow.csv", meta=None):
    return client.post(
        f"/api/projects/{pid}/datasets",
        params={"filename": name, "metadata_json": json.dumps(meta or spec())},
        content=content,
        headers={"Content-Type": "application/octet-stream"},
    )


def scenario(ids=()):
    return {
        "name": "Synthetic release",
        "forcing": {
            "mode": "prescribed_release",
            "historical": False,
            "hydrograph_dataset_id": ids[0] if ids else None,
        },
        "dataset_ids": list(ids),
        "start_time": "2025-01-01T00:00:00Z",
        "end_time": "2025-01-01T01:00:00Z",
        "time_step_seconds": 1,
        "output_interval_seconds": 60,
        "wet_threshold_m": 0.01,
        "arrival_threshold_m": 0.1,
    }


def test_hydrology_preserves_missing_gaps_flags_duplicates(tmp_path):
    p = tmp_path / "flow.csv"
    p.write_text(
        "timestamp,station_id,discharge,flag\n2025-01-01T00:00:00Z,fixture,,OK\n"
        "2025-01-01T03:00:00Z,fixture,4,BAD\n2025-01-01T03:00:00Z,fixture,5,OK\n"
    )
    r = read_hydrology(p, DatasetInput.model_validate(spec()))
    assert {i["code"] for i in r["issues"]} >= {"missing_values", "time_gaps", "duplicates", "quality_flags"}
    assert r["minimum_m3_s"] == 4 and r["interpolation"] == "none"


def test_units_and_timezones(tmp_path):
    p = tmp_path / "flow.csv"
    p.write_bytes(GOOD.replace(b"T00:00:00Z", b"T00:00:00").replace(b"T01:00:00Z", b"T01:00:00"))
    with pytest.raises(ValueError, match="source_timezone"):
        read_hydrology(p, DatasetInput.model_validate(spec()))
    meta = spec(source_timezone="Asia/Kolkata")
    meta["provenance"]["units"] = "cusec"
    r = read_hydrology(p, DatasetInput.model_validate(meta))
    assert r["minimum_m3_s"] == pytest.approx(0.028316846592)
    assert r["start_time"] == "2024-12-31T18:30:00+00:00"
    meta["provenance"]["units"] = "m"
    with pytest.raises(ValueError, match="Discharge units"):
        read_hydrology(p, DatasetInput.model_validate(meta))


@pytest.mark.parametrize(
    "name", ["../evil.csv", "..\\evil.csv", "C:\\evil.csv", "x:evil.csv", "evil.csv.exe"]
)
def test_path_traversal(env, name):
    client, _, _, path = env
    r = upload(client, project(client), name=name)
    assert r.status_code in (415, 422)
    assert not list((path / "objects").rglob("*.csv"))


def test_malformed_upload_and_limits(env):
    client, _, _, _ = env
    pid = project(client)
    assert upload(client, pid, content=b"not a csv").status_code == 422
    assert upload(client, pid, content=b"").status_code == 422
    r = client.post(
        f"/api/projects/{pid}/datasets", headers={"Content-Length": str(65 * 1024 * 1024)}, content=b"x"
    )
    assert r.status_code == 413
    assert (
        client.post("/api/projects", headers={"Origin": "https://untrusted.example"}, json={}).status_code
        == 403
    )


def test_snapshot_version_persistence_and_isolation(env):
    client, app, url, path = env
    pid = project(client)
    a = upload(client, pid)
    assert a.status_code == 201, a.text
    a = a.json()
    snap = client.post(f"/api/projects/{pid}/scenarios", json=scenario([a["id"]]))
    assert snap.status_code == 201, snap.text
    snap = snap.json()
    b = upload(client, pid, content=GOOD.replace(b",2,", b",20,")).json()
    assert b["version"] == 2 and a["sha256"] != b["sha256"]
    saved = client.get(f"/api/projects/{pid}/scenarios").json()[0]
    assert saved["snapshot"]["datasets"][0]["sha256"] == a["sha256"]
    assert saved["sha256"] == snap["sha256"]
    with pytest.raises(Exception, match="immutable"), app.state.engine.begin() as conn:
        conn.execute(text("UPDATE scenarios SET body='{}'"))
    with TestClient(create_app(url, LocalStorage(path / "objects"))) as restarted:
        assert restarted.get(f"/api/projects/{pid}/scenarios").json()[0]["sha256"] == snap["sha256"]
    other = project(client)
    assert client.post(f"/api/projects/{other}/scenarios", json=scenario([a["id"]])).status_code == 422
    assert (
        client.get(f"/api/projects/{other}/readiness", params={"scenario_id": snap["id"]}).status_code == 404
    )
    assert client.patch(f"/api/projects/{pid}/scenarios/{snap['id']}", json={}).status_code in (404, 405)
    assert client.post(f"/api/projects/{pid}/runs").status_code == 422


def test_synthetic_data_cannot_enter_real_project(env):
    client, _, _, _ = env
    assert upload(client, project(client, synthetic=False)).status_code == 422


def test_terrain_crs_and_datum(tmp_path):
    path = tmp_path / "dem.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:32631",
        transform=rasterio.transform.from_origin(500000, 1000, 10, 10),
        nodata=-9999,
    ) as dst:
        dst.write(np.array([[1, 2], [3, -9999]], dtype="float32"), 1)
    meta = spec()
    meta.pop("hydro")
    meta["kind"] = "terrain"
    meta["provenance"].update(units="m", crs="EPSG:4326")
    with pytest.raises(ValueError, match="conflicts"):
        read_terrain(path, DatasetInput.model_validate(meta))
    meta["provenance"]["crs"] = "EPSG:32631"
    report = read_terrain(path, DatasetInput.model_validate(meta))
    assert {i["code"] for i in report["issues"]} == {"terrain_nodata", "vertical_reference"}
    assert report["nodata_cells"] == 1


def test_mode_contracts_and_missing_inputs():
    data = scenario()
    data["forcing"] = {"mode": "computed_breach", "hydrograph_dataset_id": "double-count"}
    with pytest.raises(ValueError):
        ScenarioInput.model_validate(data)
    data["forcing"] = {"mode": "computed_breach", "level_storage": [[1, 3], [2, 2]]}
    with pytest.raises(ValueError, match="strictly increasing"):
        ScenarioInput.model_validate(data)
    r = assess({"vertical_reference": "unknown"}, [], ScenarioInput.model_validate(scenario()))
    assert not r["ready_for_solver"]
    assert {i["code"] for i in r["missing"]} >= {
        "terrain",
        "river",
        "datum",
        "hydrograph",
        "downstream_boundary",
    }
    assert "exposure" not in {i["code"] for i in r["missing"]}


def test_persisted_queue_and_cancel(env):
    client, app, _, _ = env
    pid = project(client)
    job = client.post(f"/api/projects/{pid}/readiness-jobs").json()
    assert job["state"] == "QUEUED"
    assert work_once(app.state.engine)
    result = client.get(f"/api/projects/{pid}/jobs").json()[0]
    assert result["state"] == "SUCCEEDED" and result["body"]["result"]["ready_for_solver"] is False
    queued = client.post(f"/api/projects/{pid}/readiness-jobs").json()
    assert client.post(f"/api/projects/{pid}/jobs/{queued['id']}/cancel").status_code == 200
    assert not work_once(app.state.engine)


def test_vector_geometry_and_crs(env):
    client, _, _, _ = env
    meta = spec()
    meta.pop("hydro")
    meta["kind"] = "river"
    meta["provenance"].update(crs="EPSG:4326", units="m")
    vector = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [0.01, 0.01]]},
            }
        ],
    }
    pid = project(client)
    assert (
        upload(client, pid, content=json.dumps(vector).encode(), name="river.geojson", meta=meta).status_code
        == 201
    )
    vector["features"][0]["geometry"] = None
    assert (
        upload(client, pid, content=json.dumps(vector).encode(), name="river.geojson", meta=meta).status_code
        == 422
    )


def test_storage_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).path("../../escape.csv")


def test_streaming_limit_without_content_length(env, monkeypatch):
    import damsafe.api

    client, _, _, _ = env
    pid = project(client)
    monkeypatch.setattr(damsafe.api, "MAX_UPLOAD", 16)
    result = client.post(
        f"/api/projects/{pid}/datasets",
        params={"filename": "flow.csv", "metadata_json": json.dumps(spec())},
        content=iter([b"1234567890", b"1234567890"]),
    )
    assert result.status_code == 413
    assert client.get(f"/api/projects/{pid}/datasets").json() == []


def test_geopackage_import(env):
    import fiona

    client, _, _, path = env
    gpkg = path / "river.gpkg"
    with fiona.open(
        gpkg,
        "w",
        driver="GPKG",
        layer="channel",
        crs="EPSG:4326",
        schema={"geometry": "LineString", "properties": {"name": "str"}},
    ) as sink:
        sink.write(
            {
                "geometry": {"type": "LineString", "coordinates": [(0, 0), (0.01, 0.01)]},
                "properties": {"name": "Synthetic channel"},
            }
        )
    meta = spec()
    meta.pop("hydro")
    meta.update(kind="river", layer="channel")
    meta["provenance"].update(crs="EPSG:4326", units="m")
    result = upload(client, project(client), content=gpkg.read_bytes(), name="river.gpkg", meta=meta)
    assert result.status_code == 201, result.text
    assert result.json()["inspection"]["feature_count"] == 1


def test_time_coverage_and_datum_readiness():
    hydro = {
        "id": "q",
        "name": "Observed fixture",
        "kind": "hydrology",
        "provenance": {"status": "observed", "synthetic": False},
        "inspection": {
            "issues": [],
            "start_time": "2025-01-01T00:30:00Z",
            "end_time": "2025-01-01T01:00:00Z",
        },
    }
    terrain = {
        "id": "dem",
        "name": "Terrain fixture",
        "kind": "terrain",
        "provenance": {"vertical_reference": "datum-A"},
        "inspection": {"issues": [], "bounds_wgs84": [0, 0, 1, 1]},
    }
    result = assess(
        {"vertical_reference": "datum-B"},
        [hydro, terrain],
        ScenarioInput.model_validate(scenario(["q", "dem"])),
    )
    codes = {i["code"] for i in result["missing"]}
    assert {"time_coverage", "datum_compatibility"} <= codes
    assert not result["ready_for_solver"]
