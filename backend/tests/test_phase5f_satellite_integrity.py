"""Tests for Phase 5F Satellite Observation Subsystem Scientific Integrity & Provenance."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from damsafe.observation.comparison import (
    compare_simulation_with_observation,
)
from damsafe.observation.gee import (
    EarthEngineService,
    ObservationMode,
    ObservationState,
    create_synthetic_test_observation,
)
from damsafe.observation.sar_processor import (
    process_authentic_sentinel1_package,
)
from damsafe.observation.sentinel1_retrieval import (
    UJJANI_MODEL_GRID_HEIGHT,
    UJJANI_MODEL_GRID_NODATA,
    UJJANI_MODEL_GRID_WIDTH,
    VERIFIED_EVENT_SCENE_ID,
)


def test_observation_states_defined_and_distinct():
    """Verify that all scientific observation readiness states are explicitly distinct."""
    states = [
        ObservationState.UNCONFIGURED,
        ObservationState.AUTHENTICATION_FAILED,
        ObservationState.AUTHENTICATED,
        ObservationState.NO_SUITABLE_SCENE,
        ObservationState.PROCESSING,
        ObservationState.OBSERVATION_READY,
        ObservationState.PROCESSING_FAILED,
        ObservationState.SYNTHETIC_TEST_DATA,
    ]
    # All states must be unique
    assert len(set(states)) == 8
    # AUTHENTICATED != OBSERVATION_AVAILABLE != PROCESSING_SUCCESS
    assert ObservationState.AUTHENTICATED != ObservationState.OBSERVATION_READY
    assert ObservationState.UNCONFIGURED != ObservationState.AUTHENTICATION_FAILED


def test_unconfigured_earth_engine_returns_data_required_without_synthetic_substitution(monkeypatch):
    """Ensure that without Earth Engine credentials, no fake 20x20 arrays are generated."""
    monkeypatch.setenv("EE_PROJECT", "")
    service = EarthEngineService()
    assert service.get_readiness_state() == ObservationState.UNCONFIGURED

    # Request a non-local historical scene
    obs = service.query_sentinel1(
        site_key="unknown-site",
        bounds_wgs84=(75.0, 15.0, 75.5, 15.5),
        mode=ObservationMode.LATEST_AVAILABLE,
    )

    assert obs.execution_state == ObservationState.UNCONFIGURED
    assert obs.grid_matrix is None
    assert obs.flooded_area_km2 == 0.0
    assert "DATA_REQUIRED" in obs.notes
    assert obs.scene_info is None


def test_synthetic_test_data_isolation():
    """Ensure test-only synthetic observation generator is explicitly tagged and isolated."""
    test_obs = create_synthetic_test_observation(
        site_key="test-reach",
        matrix=[[0, 1], [2, 3]],
        acquisition_time="2020-08-15T10:30:00Z",
    )
    assert test_obs.provenance_type == "SYNTHETIC_TEST_DATA"
    assert test_obs.execution_state == ObservationState.SYNTHETIC_TEST_DATA
    assert test_obs.scene_info is not None
    assert "SYNTHETIC_TEST_SCENE" in test_obs.scene_info.scene_id
    assert test_obs.scene_info.collection == "SYNTHETIC_TEST_COLLECTION"
    assert "SYNTHETIC_TEST_DATA" in test_obs.notes


def test_local_sar_filename_does_not_establish_authenticity(tmp_path, monkeypatch):
    """A file with a plausible name cannot bypass explicit provenance import."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EE_PROJECT", "")
    local_mask = Path("data/processed/sentinel1/UJJANI_20201019_flood_mask.tif")
    local_mask.parent.mkdir(parents=True)
    local_mask.write_bytes(b"not an authenticated observation")
    service = EarthEngineService()
    obs = service.query_sentinel1(
        site_key="ujjani-bhima",
        bounds_wgs84=(74.6, 17.65, 75.95, 18.35),
        mode=ObservationMode.HISTORICAL_EVENT,
        target_time="2020-10-19T00:55:11Z",
    )

    assert obs.execution_state == ObservationState.UNCONFIGURED
    assert obs.grid_matrix is None
    assert obs.scene_info is None


def test_comparison_validation_rejects_empty_simulation():
    """Comparison must reject empty or missing simulation results."""
    obs = create_synthetic_test_observation(matrix=[[0, 1], [1, 0]])
    with pytest.raises(ValueError, match="simulation result grid is empty"):
        compare_simulation_with_observation(
            run_id="run-1",
            sim_grid=[],
            observation=obs,
            sim_frame_time="2020-08-15T10:30:00Z",
        )


def test_comparison_validation_rejects_unready_observation():
    """Comparison must reject observations in unconfigured / failed states."""
    service = EarthEngineService()
    unready_obs = service.query_sentinel1(
        site_key="unknown-site",
        bounds_wgs84=(75.0, 15.0, 75.5, 15.5),
        mode=ObservationMode.LATEST_AVAILABLE,
    )
    with pytest.raises(ValueError, match="observation is in state"):
        compare_simulation_with_observation(
            run_id="run-1",
            sim_grid=[[0, 1], [1, 0]],
            observation=unready_obs,
            sim_frame_time="2020-08-15T10:30:00Z",
        )


def test_comparison_validation_rejects_spatial_dimension_mismatch():
    """Comparison must reject grids with mismatched spatial dimensions."""
    obs = create_synthetic_test_observation(matrix=[[0, 1], [1, 0]])  # 2x2
    sim_grid = [[0, 1, 0], [1, 0, 1], [0, 0, 0]]  # 3x3

    with pytest.raises(ValueError, match="Spatial resolution / dimension mismatch"):
        compare_simulation_with_observation(
            run_id="run-1",
            sim_grid=sim_grid,
            observation=obs,
            sim_frame_time="2020-08-15T10:30:00Z",
        )


def test_comparison_validation_records_temporal_delta():
    """Comparison must compute and record temporal delta between simulation frame and satellite acquisition."""
    obs = create_synthetic_test_observation(
        matrix=[[1, 0], [0, 1]],
        acquisition_time="2020-10-19T00:55:11Z",
    )
    sim_grid = [[1, 0], [0, 1]]

    # 2 hours later
    res = compare_simulation_with_observation(
        run_id="run-1",
        sim_grid=sim_grid,
        observation=obs,
        sim_frame_time="2020-10-19T02:55:11Z",
    )
    assert res.temporal_delta_hours == 2.0
    assert res.is_interpolated is True
    assert res.iou == 1.0
    assert res.f1_score == 1.0
    assert res.validation_status == "VALIDATED"


def test_geospatial_reprojection_preserves_nodata_and_crs(tmp_path):
    """Verify that sar_processor performs genuine reprojection and preserves nodata."""
    # Create input GeoTIFF with EPSG:4326
    raw_tif = tmp_path / f"{VERIFIED_EVENT_SCENE_ID}.tif"
    data = np.full((50, 50), -12.0, dtype=np.float32)
    data[0:10, 0:10] = UJJANI_MODEL_GRID_NODATA  # Nodata block

    transform = rasterio.transform.from_bounds(74.6, 17.65, 75.95, 18.35, 50, 50)
    profile = {
        "driver": "GTiff",
        "height": 50,
        "width": 50,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": UJJANI_MODEL_GRID_NODATA,
    }
    with rasterio.open(raw_tif, "w", **profile) as dst:
        dst.write(data, 1)

    out_dir = tmp_path / "processed"
    out_file, prov = process_authentic_sentinel1_package(raw_tif, out_dir, "EVENT")

    assert out_file.exists()
    assert prov.crs == "EPSG:32643"
    assert prov.resolution_m == 10.0

    with rasterio.open(out_file) as src:
        assert src.crs.to_string() == "EPSG:32643"
        assert src.width == UJJANI_MODEL_GRID_WIDTH
        assert src.height == UJJANI_MODEL_GRID_HEIGHT
        assert src.nodata == UJJANI_MODEL_GRID_NODATA


def test_historical_validation_rejects_synthetic_data():
    """Historical validation mode must strictly reject synthetic test data."""
    obs = create_synthetic_test_observation(
        matrix=[[1, 0], [0, 1]],
        acquisition_time="2020-10-19T00:55:11Z",
    )
    with pytest.raises(ValueError, match="strictly prohibited from historical validation"):
        compare_simulation_with_observation(
            run_id="run-1",
            sim_grid=[[1, 0], [0, 1]],
            observation=obs,
            sim_frame_time="2020-10-19T00:55:11Z",
            is_historical_validation=True,
        )


def test_comparison_rejects_invalid_timestamp_formats():
    """Comparison must reject unparseable timestamp formats rather than silently setting delta to 0."""
    obs = create_synthetic_test_observation(
        matrix=[[1, 0], [0, 1]],
        acquisition_time="invalid-date-format",
    )
    with pytest.raises(ValueError, match="Invalid ISO-8601 timestamp format"):
        compare_simulation_with_observation(
            run_id="run-1",
            sim_grid=[[1, 0], [0, 1]],
            observation=obs,
            sim_frame_time="2020-10-19T00:55:11Z",
            is_historical_validation=False,
        )


def test_sar_processor_fails_on_missing_crs(tmp_path):
    """sar_processor must fail explicitly when source raster lacks georeferencing."""
    raw_tif = tmp_path / f"{VERIFIED_EVENT_SCENE_ID}.tif"
    data = np.full((10, 10), -15.0, dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": 10,
        "width": 10,
        "count": 1,
        "dtype": "float32",
        "crs": None,
        "transform": None,
    }
    with rasterio.open(raw_tif, "w", **profile) as dst:
        dst.write(data, 1)

    with pytest.raises(ValueError, match="Missing CRS or affine geospatial transform"):
        process_authentic_sentinel1_package(raw_tif, tmp_path / "out", "EVENT")
