"""Synthetic software fixtures and process harnesses; not native engine smoke tests."""

import sys
import time

import netCDF4
import numpy as np
import pytest
from alembic import command
from alembic.config import Config
from damsafe.api import create_app
from damsafe.db import runs
from damsafe.numerics import adapters, service, worker
from damsafe.numerics.diagnostics import (
    compare_series,
    extent_agreement,
    prescribed_storage_balance,
    volume_balance,
)
from damsafe.numerics.execution import Limits, execute, within
from damsafe.numerics.results import normalize_dflow, validate_result
from damsafe.numerics.sph import read_partvtk
from damsafe.storage import LocalStorage
from fastapi.testclient import TestClient


def test_process_harness_nonzero_missing_timeout_and_cancel(tmp_path):
    limits = Limits(timeout_seconds=2)
    for args in [[str(tmp_path / "absent.exe")], [sys.executable, "-c", "raise SystemExit(7)"]]:
        result = execute(args, tmp_path, tmp_path / "run.log", limits)
        assert result["state"] == "FAILED"
    result = execute(
        [sys.executable, "-c", "import time;time.sleep(10)"],
        tmp_path,
        tmp_path / "timeout.log",
        Limits(timeout_seconds=0.25),
    )
    assert result["state"] == "FAILED" and "Wall-time" in result["error"]
    start = time.monotonic()
    result = execute(
        [sys.executable, "-c", "import time;time.sleep(10)"],
        tmp_path,
        tmp_path / "cancel.log",
        limits,
        cancelled=lambda: time.monotonic() - start > 0.25,
    )
    assert result["state"] == "CANCELLED"
    assert result["elapsed_seconds"] < 5


def test_case_paths_and_log_limit(tmp_path):
    with pytest.raises(ValueError):
        within(tmp_path, "../escape")
    result = execute(
        [sys.executable, "-c", 'print("x"*10000)'], tmp_path, tmp_path / "log", Limits(log_bytes=100)
    )
    assert result["state"] == "FAILED"
    assert (tmp_path / "log").stat().st_size <= 100


def test_dflow_zero_exit_with_native_error_or_truncated_map_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "f34_map.nc").write_bytes(b"native output placeholder")

    def fake_execute(argv, directory, log, limits, cancelled, progress, name):
        log.write_text("** ERROR : time step fell below minimum\n", encoding="utf-8")
        return {"state": "SUCCEEDED", "exit_code": 0}

    monkeypatch.setattr(adapters, "execute", fake_execute)
    outcome = adapters.run_stages(
        "dflowfm", tmp_path, "00000000-0000-4000-8000-000000000001",
        {"available": True, "image_id": "test-only"}, Limits(),
    )
    assert outcome["state"] == "FAILED" and "native log" in outcome["reason"]

    monkeypatch.setattr(
        worker, "normalize_dflow", lambda *args, **kwargs: {"duration_seconds": 0.05}
    )
    with pytest.raises(ValueError, match="stopped before"):
        worker.finalize("dflowfm", tmp_path, {"physical_case": {"end_time_s": 2}}, {})


def dflow_fixture(path, negative=False, stagger=False):
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", 2)
        ds.createDimension("mesh2d_nFaces", 2)
        ds.createDimension("mesh2d_nNodes", 2)
        t = ds.createVariable("time", "f8", ("time",))
        t.units = "seconds since 2025-01-01 00:00:00"
        t[:] = [0, 60]
        for name, data, unit in [
            ("mesh2d_face_x", [0, 1], "m"),
            ("mesh2d_face_y", [0, 0], "m"),
            ("mesh2d_flowelem_ba", [1, 1], "m2"),
            ("mesh2d_flowelem_bl", [0, 0], "m"),
        ]:
            v = ds.createVariable(name, "f8", ("mesh2d_nFaces",))
            v.units = unit
            v[:] = data
        h = ds.createVariable("mesh2d_waterdepth", "f8", ("time", "mesh2d_nFaces"), fill_value=-9999)
        h.units = "m"
        h[:] = [[-1 if negative else 1, -9999], [0.5, 0]]
        if stagger:
            v = ds.createVariable("mesh2d_ucx", "f8", ("time", "mesh2d_nNodes"))
            v[:] = 0
            v.units = "m/s"


def test_native_netcdf_parser_missing_fields_and_masks(tmp_path):
    native = tmp_path / "source.nc"
    out = tmp_path / "normalized.nc"
    dflow_fixture(native)
    r = normalize_dflow(
        native, out, crs="fixture-local", datum="fixture", threshold=0.01, source_provenance={"fixture": True}
    )
    assert r["frames"] == 2 and r["provenance"]["unavailable_fields"] == ["eta", "u", "v"]
    with netCDF4.Dataset(out) as ds:
        assert ds["h"][0].mask.tolist() == [False, True]
        assert ds["u"][:].mask.all()
        assert ds["wet"][1].tolist() == [1, 0]
    with netCDF4.Dataset(out, "a") as ds:
        ds["wet"][1, 0] = 0
    with pytest.raises(ValueError, match="mask disagreement"):
        validate_result(out)


@pytest.mark.parametrize("negative,stagger", [(True, False), (False, True)])
def test_invalid_native_output_rejected(tmp_path, negative, stagger):
    path = tmp_path / "source.nc"
    dflow_fixture(path, negative, stagger)
    with pytest.raises(ValueError):
        normalize_dflow(
            path, tmp_path / "out.nc", crs="local", datum="fixture", threshold=0.01, source_provenance={}
        )


def test_binary_partvtk_endianness_and_corruption(tmp_path):
    """Exercise the binary POLYDATA wire format used by the genuine CPU run."""
    path = tmp_path / "PartFluid_0000.vtk"
    payload = b"".join(
        [
            b"# vtk DataFile Version 3.0\nvtk output\nBINARY\nDATASET POLYDATA\n",
            b"POINTS 2 float\n",
            np.asarray([[0.25, 0, 1], [0.75, 0, 0.5]], dtype=">f4").tobytes(),
            b"\nVERTICES 2 4\n",
            np.asarray([[1, 0], [1, 1]], dtype=">i4").tobytes(),
            b"\nPOINT_DATA 2\nSCALARS Idp unsigned_int\nLOOKUP_TABLE default\n",
            np.asarray([1, 2], dtype=">u4").tobytes(),
            b"\nFIELD FieldData 4\n",
        ]
    )
    for name, values, dtype in [
        ("Vel", [[1, 0, -2], [3, 0, 4]], ">f4"),
        ("Rhop", [[1000], [1002]], ">f4"),
        ("Press", [[0], [0]], ">f4"),
        ("Type", [[1], [1]], "u1"),
    ]:
        array = np.asarray(values, dtype=dtype)
        vtk_type = "unsigned_char" if dtype == "u1" else "float"
        payload += f"{name} {array.shape[1]} 2 {vtk_type}\n".encode() + array.tobytes() + b"\n"
    path.write_bytes(payload)
    points, density, velocity = read_partvtk(path)
    assert points[:, 2].tolist() == [1, 0.5]
    assert density.tolist() == [1000, 1002]
    assert velocity[:, 0].tolist() == [1, 3]
    path.write_bytes(payload[:-4])
    with pytest.raises(ValueError):
        read_partvtk(path)


def test_continuity_against_analytical_constant_release():
    r = prescribed_storage_balance([0, 10, 20], 100, [1, 1, 1], {"outlet": [3, 3, 3]}, [[0, 0], [10, 200]])
    assert r["storage_m3"] == [100, 80, 60]
    assert r["level_m"] == [5, 4, 3]
    assert r["balance"]["maximum_absolute_residual_m3"] == 0
    with pytest.raises(ValueError, match="available water"):
        prescribed_storage_balance([0, 100], 100, [0, 0], {"outlet": [2, 2]}, [[0, 0], [10, 200]])
    r = volume_balance([0, 1, 2], [10, 10, 10], [0, 0, 0], [0, 0, 0])
    assert r["maximum_absolute_residual_m3"] == 0
    # Endpoints conserve storage, but a linear flux ramp empties the reservoir mid-step.
    with pytest.raises(ValueError, match="available water"):
        prescribed_storage_balance([0,10],1,[0,2],{"outlet":[2,0]},[[0,0],[10,200]])


def test_agreement_requires_physical_and_temporal_compatibility():
    r = compare_series([0, 1], [1, 3], [0, 1], [2, 3], compatible_case_hash_a="a", compatible_case_hash_b="a")
    assert r["rmse"] == pytest.approx(np.sqrt(0.5))
    with pytest.raises(ValueError):
        compare_series([0, 1], [1, 3], [0, 2], [2, 3], compatible_case_hash_a="a", compatible_case_hash_b="a")
    with pytest.raises(ValueError):
        compare_series([0, 1], [1, 3], [0, 1], [2, 3], compatible_case_hash_a="a", compatible_case_hash_b="b")
    assert extent_agreement([0], [0], [1], [1])["iou"] is None
    r = extent_agreement([1, 1], [1, 0], [1, 0], [2, 3])
    assert r["iou"] == 1 and r["valid_area_m2"] == 2


def test_run_api_idempotency_cancel_and_failed_normalization(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path.as_posix()}/runs.db"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", url)
    monkeypatch.setenv("DAMSAFE_RUN_ROOT", str(tmp_path / "runs"))
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(url, LocalStorage(tmp_path / "objects"))
    monkeypatch.setattr(
        service, "capabilities", lambda _: {"available": True, "image_id": "test-harness-only"}
    )
    with TestClient(app) as client:
        pid = client.post(
            "/api/projects", json={"name": "TEST HARNESS", "site_key": "test", "synthetic": True}
        ).json()["id"]
        request = {
            "engine": "dualsphysics",
            "case_kind": "OFFICIAL_EXAMPLE",
            "idempotency_key": "test-harness-001",
        }
        first = client.post(f"/api/projects/{pid}/runs", json=request)
        assert first.status_code == 202, first.text
        again = client.post(f"/api/projects/{pid}/runs", json=request)
        assert again.json()["id"] == first.json()["id"]
        conflict = client.post(f"/api/projects/{pid}/runs", json={**request, "particle_spacing_m": 0.02})
        assert conflict.status_code == 409
        ident = first.json()["id"]
        assert client.post(f"/api/projects/{pid}/runs/{ident}/cancel").status_code == 200
        assert not worker.work_once(app.state.engine)
        second = client.post(
            f"/api/projects/{pid}/runs", json={**request, "idempotency_key": "test-harness-002"}
        ).json()

        def prepare(_, destination, __):
            destination.mkdir(parents=True)
            return {"fixture": True}

        monkeypatch.setattr(worker, "prepare_official", prepare)
        monkeypatch.setattr(
            worker, "run_stages", lambda *args, **kwargs: {"state": "SUCCEEDED", "stages": []}
        )

        def corrupt(*args):
            raise ValueError("corrupted output fixture")

        monkeypatch.setattr(worker, "finalize", corrupt)
        assert worker.work_once(app.state.engine)
        all_runs = client.get(f"/api/projects/{pid}/runs").json()
        result = next(r for r in all_runs if r["id"] == second["id"])
        assert result["state"] == "FAILED" and "corrupted" in result["result"]["error"]
        with pytest.raises(Exception, match="immutable"), app.state.engine.begin() as conn:
            conn.execute(runs.update().where(runs.c.id == second["id"]).values(input={}))
        third = client.post(
            f"/api/projects/{pid}/runs", json={**request, "idempotency_key": "test-harness-003"}
        ).json()
        with app.state.engine.begin() as conn:
            conn.execute(
                runs.update()
                .where(runs.c.id == third["id"])
                .values(state="RUNNING", result={"heartbeat_at": "2000-01-01T00:00:00+00:00"})
            )
        removed = []
        monkeypatch.setattr(worker.subprocess, "run", lambda argv, **kwargs: removed.append(argv))
        assert worker.recover_stale(app.state.engine) == [third["id"]]
        assert len(removed) == 3 and all(third["id"] in argv[-1] for argv in removed)
        assert next(r for r in client.get(f"/api/projects/{pid}/runs").json() if r["id"] == third["id"])["state"] == "FAILED"
