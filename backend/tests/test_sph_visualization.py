
import pytest
from damsafe.api import create_app
from damsafe.numerics.sph_adapter import (
    find_sph_run_dir,
    get_sph_frame,
    get_sph_metadata,
    list_available_sph_runs,
)
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_sph.db"
    app = create_app(f"sqlite:///{db_path}")
    return TestClient(app)


def test_list_sph_runs():
    runs = list_available_sph_runs()
    assert len(runs) >= 2
    assert "424a48cf-e381-4599-ac9a-25817559fe09" in runs
    assert "7eac17d0-15d0-4113-91b1-8f3461329a5c" in runs


def test_sph_metadata_and_frame_extraction():
    run_dir = find_sph_run_dir("424a48cf-e381-4599-ac9a-25817559fe09")
    assert run_dir is not None
    assert run_dir.exists()

    meta = get_sph_metadata(run_dir)
    assert meta["solver"] == "DualSPHysics"
    assert meta["case_id"] == "CaseDambreakVal2D"
    assert meta["classification"] == "LABORATORY_BENCHMARK"
    assert meta["particle_count"] == 20000
    assert meta["boundary_particle_count"] == 1001
    assert meta["frames_count"] == 201
    assert meta["simulation_duration_s"] == 2.0
    assert len(meta["times"]) == 201
    assert meta["bounds"]["x_min"] <= 0.0
    assert meta["bounds"]["x_max"] >= 4.0

    # Test reading frame 0 and frame 100
    f0 = get_sph_frame(run_dir, 0, decimation=1)
    assert f0["frame_index"] == 0
    assert f0["time_seconds"] == 0.0
    assert f0["particle_count"] == 20000
    assert len(f0["particles"]) == 20000
    assert len(f0["flat_positions"]) == 60000
    assert f0["max_velocity"] >= 0.0

    f100 = get_sph_frame(run_dir, 100, decimation=2)
    assert f100["frame_index"] == 100
    assert f100["time_seconds"] == 1.0
    assert f100["particle_count"] == 10000
    assert f100["decimation_stride"] == 2
    assert f100["max_velocity"] > 1.0


def test_sph_api_endpoints(client):
    # Test listing endpoint
    res_list = client.get("/api/sph/runs")
    assert res_list.status_code == 200
    runs = res_list.json()["runs"]
    assert len(runs) >= 2

    # Test metadata endpoint
    run_id = "424a48cf-e381-4599-ac9a-25817559fe09"
    res_meta = client.get(f"/api/runs/{run_id}/sph/metadata")
    assert res_meta.status_code == 200
    meta = res_meta.json()
    assert meta["solver"] == "DualSPHysics"
    assert meta["particle_count"] == 20000
    assert meta["frames_count"] == 201
    assert "LABORATORY BENCHMARK" in meta["classification_badge"]

    # Test frame endpoint
    res_f = client.get(f"/api/runs/{run_id}/sph/frame?index=50&decimation=4")
    assert res_f.status_code == 200
    frame = res_f.json()
    assert frame["frame_index"] == 50
    assert frame["time_seconds"] == 0.5
    assert frame["particle_count"] == 5000
    assert frame["decimation_stride"] == 4
    assert len(frame["flat_positions"]) == 15000

    # Test non-existent run
    res_404 = client.get("/api/runs/non-existent-run-id/sph/metadata")
    assert res_404.status_code == 404
