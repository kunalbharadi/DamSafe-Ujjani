"""Phase 3 contracts; one opt-in case reads retained genuine solver output."""

import os
import shutil
from pathlib import Path

import netCDF4
import numpy as np
import pytest
from alembic import command
from alembic.config import Config
from damsafe.api import create_app
from damsafe.contracts import RunRequest
from damsafe.db import projects, runs
from damsafe.numerics import service
from damsafe.numerics.execution import sha256
from damsafe.numerics.products import named_location, postprocess, product_window, window
from damsafe.numerics.results import create_result, write_frame
from damsafe.storage import LocalStorage
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import insert

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / ".local/runs/5f337ace-316f-487b-8962-330e97a11685/normalized.nc"
NATIVE_ID = "5f337ace-316f-487b-8962-330e97a11685"


def test_products_preserve_arrival_dry_nodata_and_underlying_statistics(tmp_path):
    source, target = tmp_path / "normalized.nc", tmp_path / "products.nc"
    with create_result(source, [0, 1, 3], [0, 1, 2, 3], [0, 0, 0, 0],
                       [2, 3, 4, 5], [0] * 4, {"fixture": True}, .01) as ds:
        write_frame(ds, 0, np.ma.masked_invalid([0, 0, np.nan, 0]), u=[0] * 4, v=[0] * 4)
        write_frame(ds, 1, np.ma.masked_invalid([.2, 0, np.nan, np.nan]), u=[2] * 4, v=[0] * 4)
        write_frame(ds, 2, np.ma.masked_invalid([.1, 0, np.nan, 0]), u=[1] * 4, v=[0] * 4)
    report = postprocess(source, target, threshold_m=.1)
    assert report["status"] == "COMPUTED_FROM_SAVED_NUMERICAL_OUTPUT"
    with netCDF4.Dataset(target) as ds:
        assert ds["cell_state"][:].tolist() == [2, 1, 0, 0]
        assert float(ds["arrival_elapsed_s"][0]) == 1
        assert float(ds["flood_duration_s"][0]) == 2
        assert float(ds["maximum_depth_m"][0]) == pytest.approx(.2)
        assert float(ds["maximum_velocity_m_s"][0]) == 2
        assert ds["flooded_area_m2"][:].tolist() == [0, 2, 2]
        assert ds["unknown_area_m2"][:].tolist() == [4, 9, 4]
        assert ds["valid_frame_count"][:].tolist() == [3, 3, 0, 2]
        assert np.ma.is_masked(ds["arrival_elapsed_s"][1])
        assert np.ma.is_masked(ds["flood_duration_s"][2])
    selected = product_window(target, (-1, -1, 4, 1), "arrival_elapsed_s")
    assert [cell["state"] for cell in selected["cells"]] == ["REACHED", "NOT_REACHED", "NODATA", "NODATA"]
    raw = window(source, (-1, -1, 4, 1), first_frame=1, frame_count=1, field="h")
    assert raw["frames"][0]["states"] == ["WET", "DRY", "NODATA", "NODATA"]
    reached = named_location(source, target, name="Gauge A", x=0, y=0, radius_m=.1)
    assert reached["state"] == "REACHED" and reached["arrival_elapsed_s"] == 1
    missing = named_location(source, target, name="Beyond", x=99, y=99, radius_m=1)
    assert missing["state"] == "OUTSIDE_DOMAIN"
    with pytest.raises(ValueError, match="bounded frame"):
        window(source, (-1, -1, 4, 1), first_frame=0, frame_count=33, field="h")


def test_window_refuses_more_than_2048_cells(tmp_path):
    source = tmp_path / "large.nc"
    n = 2049
    with create_result(source, [0, 1], np.arange(n), np.zeros(n), np.ones(n),
                       np.zeros(n), {"fixture": True}, .01) as ds:
        write_frame(ds, 0, np.zeros(n))
        write_frame(ds, 1, np.zeros(n))
    with pytest.raises(ValueError, match="2048 cells"):
        window(source, (-1, -1, n + 1, 1), first_frame=0, frame_count=1, field="h")


def test_site_scenario_identity_changes_and_cannot_attach_to_official_example():
    cap = {"image_id": "sha256:" + "a" * 64}
    a = RunRequest(engine="dflowfm", case_kind="SITE_SCENARIO",
                   scenario_id="immutable-snapshot-a", idempotency_key="site-key-a")
    b = RunRequest(engine="dflowfm", case_kind="SITE_SCENARIO",
                   scenario_id="immutable-snapshot-b", idempotency_key="site-key-b")
    assert service.configuration_hash(a, cap) != service.configuration_hash(b, cap)
    with pytest.raises(ValidationError, match="unrelated site scenario"):
        RunRequest(engine="dflowfm", case_kind="OFFICIAL_EXAMPLE",
                   scenario_id="immutable-snapshot-a", idempotency_key="official-key")


@pytest.mark.skipif(not NATIVE.exists() and os.getenv("DAMSAFE_REQUIRE_NATIVE_EVIDENCE") != "1",
                    reason="Retained genuine D-Flow output unavailable in this checkout")
def test_genuine_saved_solver_result_is_run_isolated_and_matches_native(tmp_path, monkeypatch):
    assert NATIVE.is_file(), "Native evidence required for this integration check"
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(tmp_path / "runs"))
    database = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", database)
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(database, LocalStorage(tmp_path / "objects"))
    stored = tmp_path / "runs" / NATIVE_ID
    stored.mkdir(parents=True)
    shutil.copyfile(NATIVE, stored / "normalized.nc")
    product = postprocess(stored / "normalized.nc", stored / "products.nc", threshold_m=.01)
    assert product["source_normalized_sha256"] == sha256(NATIVE)
    with app.state.engine.begin() as conn:
        conn.execute(insert(projects).values(id="lab", body={"name": "Native laboratory case", "synthetic": True}))
        conn.execute(insert(projects).values(id="other", body={"name": "Other laboratory case", "synthetic": True}))
        conn.execute(insert(runs).values(id=NATIVE_ID, project_id="lab", idempotency_key="native-archive-001",
            state="SUCCEEDED", input={"request": {"scenario_id": None}, "configuration_hash": "native-shared-case"},
            result={"normalization": {"normalized_sha256": sha256(NATIVE)}, "postprocessing": product}))
        conn.execute(insert(runs).values(id="00000000-0000-4000-8000-000000000002", project_id="lab",
            idempotency_key="other-run-001", state="SUCCEEDED",
            input={"request": {"scenario_id": None}, "configuration_hash": "different-case"},
            result={"normalization": {"normalized_sha256": sha256(NATIVE)}}))
    with TestClient(app) as client:
        prefix = f"/api/projects/lab/runs/{NATIVE_ID}"
        meta = client.get(prefix + "/results/metadata")
        assert meta.status_code == 200 and meta.json()["source_run_id"] == NATIVE_ID
        assert meta.json()["engine"] == "dflowfm"
        assert meta.json()["nodata_value"] == {"floating": "NaN", "wet": -1, "valid": 0}
        area = client.get(prefix + "/products/area", params={"first_frame": 0, "frame_count": 1})
        with netCDF4.Dataset(NATIVE) as ds:
            native_area = float(np.sum(np.asarray(ds["cell_area"][:]) *
                                       (np.asarray(ds["h"][0]) >= .01)))
        assert area.status_code == 200
        assert area.json()["frames"][0]["flooded_area_m2"] == pytest.approx(native_area)
        assert client.get(prefix + "/results/window", params={"bbox": "0,0,4,1", "frame_count": 33}).status_code == 422
        assert client.get(f"/api/projects/other/runs/{NATIVE_ID}/results/metadata").status_code == 404
        assert client.get("/api/projects/lab/runs/00000000-0000-4000-8000-000000000002/results/metadata").status_code == 409


def test_identical_configuration_caches_only_verified_output_and_changed_config_gets_new_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(tmp_path / "runs"))
    database = f"sqlite:///{(tmp_path / 'cache.db').as_posix()}"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", database)
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(database, LocalStorage(tmp_path / "objects"))
    cap = {"available": True, "engine": "dualsphysics", "image_id": "sha256:" + "a" * 64}
    monkeypatch.setattr(service, "capabilities", lambda _: cap)
    first_request = RunRequest(engine="dualsphysics", case_kind="OFFICIAL_EXAMPLE", idempotency_key="first-key")
    config = service.configuration_hash(first_request, cap)
    first_id = "00000000-0000-4000-8000-000000000011"
    directory = tmp_path / "runs" / first_id
    directory.mkdir(parents=True)
    with create_result(directory / "normalized.nc", [0, 1], [0], [0], [1], [0],
                       {"fixture": True}, .01) as ds:
        write_frame(ds, 0, [0])
        write_frame(ds, 1, [1])
    checksum = sha256(directory / "normalized.nc")
    products = postprocess(directory / "normalized.nc", directory / "products.nc", threshold_m=.01)
    with app.state.engine.begin() as conn:
        conn.execute(insert(projects).values(id="lab", body={"name": "Synthetic fixture lab", "synthetic": True}))
        conn.execute(insert(runs).values(id=first_id, project_id="lab", idempotency_key="first-key",
            state="SUCCEEDED", input={"request": first_request.model_dump(mode="json"),
                                      "configuration_hash": config},
            result={"normalization": {"normalized_sha256": checksum}, "postprocessing": products}))
    cached = service.submit(app.state.engine, "lab", RunRequest(
        engine="dualsphysics", case_kind="OFFICIAL_EXAMPLE", idempotency_key="second-key"))
    assert cached["id"] != first_id and cached["state"] == "SUCCEEDED"
    assert cached["result"]["cached_from_run_id"] == first_id
    assert cached["result"]["cache_status"] == "VALID_IDENTICAL_CONFIGURATION"
    with TestClient(app) as client:
        cached_metadata = client.get(f"/api/projects/lab/runs/{cached['id']}/results/metadata")
        assert cached_metadata.status_code == 200
        assert cached_metadata.json()["cached"] is True
        assert cached_metadata.json()["source_run_id"] == first_id
    changed = service.submit(app.state.engine, "lab", RunRequest(
        engine="dualsphysics", case_kind="OFFICIAL_EXAMPLE", particle_spacing_m=.02,
        idempotency_key="third-key"))
    assert changed["id"] not in {first_id, cached["id"]} and changed["state"] == "QUEUED"
    assert changed["input"]["configuration_hash"] != config
    (directory / "normalized.nc").write_bytes(b"corrupted")
    fresh = service.submit(app.state.engine, "lab", RunRequest(
        engine="dualsphysics", case_kind="OFFICIAL_EXAMPLE", idempotency_key="fourth-key"))
    assert fresh["state"] == "QUEUED"  # corrupt prior output cannot satisfy the cache
