"""Tests for Phase 5C Sentinel-1 Retrieval Configuration, Ingestion & EPSG:32643 Spatial Contract."""

import hashlib
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from damsafe.observation.gee import EarthEngineService
from damsafe.observation.sar_processor import (
    create_standard_aligned_geotiff,
    process_authentic_sentinel1_package,
)
from damsafe.observation.sentinel1_retrieval import (
    UJJANI_MODEL_GRID_AFFINE,
    UJJANI_MODEL_GRID_BOUNDS,
    VERIFIED_EVENT_SCENE_ID,
    VERIFIED_PRE_EVENT_SCENE_ID,
    ProcessedSARProvenance,
    UjjaniSARGridSpec,
    calculate_file_sha256,
    get_october_2020_scene_manifest,
    validate_scene_id,
)


def test_verified_sentinel1_scene_manifest():
    manifest = get_october_2020_scene_manifest()
    # Event scene
    assert manifest["scene_id"] == VERIFIED_EVENT_SCENE_ID
    assert manifest["satellite"] == "Sentinel-1A"
    assert manifest["acquisition_utc"] == "2020-10-19T00:55:11Z"
    assert manifest["orbit_direction"] == "DESCENDING"
    assert manifest["relative_orbit"] == 136
    assert manifest["instrument_mode"] == "IW"
    assert manifest["product_type"] == "GRDH"
    assert manifest["polarization"] == "VV+VH"
    assert manifest["model_reach_intersected"] is True
    assert manifest["processed_crs"] == "EPSG:32643"

    # Pre-event scene
    assert manifest["pre_event_scene_id"] == VERIFIED_PRE_EVENT_SCENE_ID
    assert manifest["pre_event_acquisition_utc"] == "2020-10-07T00:55:14Z"
    assert manifest["pre_event_relative_orbit"] == 136
    assert manifest["temporal_gap_days"] == 12

    # Authentication status
    assert manifest["live_earth_engine_status"] == "BLOCKED"
    assert manifest["authentic_artifact_obtained"] is False


def test_processed_spatial_contract_epsg32643():
    grid = UjjaniSARGridSpec()
    assert grid.crs == "EPSG:32643"
    assert grid.bounds_utm43n == (512700.0, 1955900.0, 534900.0, 1999100.0)
    assert grid.pixel_size_m == 10.0
    assert grid.width == 2220
    assert grid.height == 4320
    assert grid.nodata == -9999.0
    assert grid.affine_transform == (10.0, 0.0, 512700.0, 0.0, -10.0, 1999100.0)
    assert "Reprojection to EPSG:32643" in grid.resolution_note


def test_event_and_preevent_share_identical_spatial_contract():
    event_prov = ProcessedSARProvenance(
        product_id=VERIFIED_EVENT_SCENE_ID,
        role="EVENT",
        acquisition_utc="2020-10-19T00:55:11Z",
        source_artifact_sha256="event_hash_123",
        source_format="zip",
        processing_steps=["calibrate", "clip", "reproject"],
        processed_output_sha256="out_hash_event",
    )

    preevent_prov = ProcessedSARProvenance(
        product_id=VERIFIED_PRE_EVENT_SCENE_ID,
        role="PRE_EVENT",
        acquisition_utc="2020-10-07T00:55:14Z",
        source_artifact_sha256="preevent_hash_456",
        source_format="zip",
        processing_steps=["calibrate", "clip", "reproject"],
        processed_output_sha256="out_hash_preevent",
    )

    # Identical spatial parameters
    assert event_prov.crs == preevent_prov.crs == "EPSG:32643"
    assert event_prov.clip_bounding_box_utm43n == preevent_prov.clip_bounding_box_utm43n == UJJANI_MODEL_GRID_BOUNDS
    assert event_prov.resolution_m == preevent_prov.resolution_m == 10.0
    assert event_prov.nodata_value == preevent_prov.nodata_value == -9999.0
    assert event_prov.affine_transform == preevent_prov.affine_transform == UJJANI_MODEL_GRID_AFFINE


def test_scene_id_validation_and_rejection():
    # Valid event ID
    assert validate_scene_id(VERIFIED_EVENT_SCENE_ID, "EVENT") is True

    # Valid pre-event ID
    assert validate_scene_id(VERIFIED_PRE_EVENT_SCENE_ID, "PRE_EVENT") is True

    # Rejection of unverified candidate ID
    with pytest.raises(ValueError, match="Invalid event scene ID"):
        validate_scene_id("S1A_IW_GRDH_1SDV_20201017T004312_20201017T004337_034829_040EB4_B468", "EVENT")

    # Rejection of swapped roles
    with pytest.raises(ValueError, match="Invalid event scene ID"):
        validate_scene_id(VERIFIED_PRE_EVENT_SCENE_ID, "EVENT")

    with pytest.raises(ValueError, match="Invalid pre-event scene ID"):
        validate_scene_id(VERIFIED_EVENT_SCENE_ID, "PRE_EVENT")


def test_sha256_checksum_calculation():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"DamSafe Authentic Sentinel-1 GRD Test Stream")
        tmp_path = Path(tmp.name)

    try:
        calculated_sha = calculate_file_sha256(tmp_path)
        expected_sha = hashlib.sha256(b"DamSafe Authentic Sentinel-1 GRD Test Stream").hexdigest()
        assert calculated_sha == expected_sha
    finally:
        tmp_path.unlink()


def test_sar_package_ingestion_and_provenance(tmp_path):
    # 1. Create a mock authentic zip package with measurement TIFF
    raw_zip = tmp_path / f"{VERIFIED_EVENT_SCENE_ID}.zip"
    meas_tif = tmp_path / "measurement.tif"
    create_standard_aligned_geotiff(meas_tif, np.full((100, 100), -12.0, dtype=np.float32))

    with zipfile.ZipFile(raw_zip, "w") as zf:
        zf.write(meas_tif, arcname=f"{VERIFIED_EVENT_SCENE_ID}.SAFE/measurement/s1a-iw-grd-vv-20201019.tiff")
        zf.writestr(f"{VERIFIED_EVENT_SCENE_ID}.SAFE/manifest.safe", "<manifest/>")
    meas_tif.unlink()

    out_dir = tmp_path / "processed"
    out_tif, prov = process_authentic_sentinel1_package(raw_zip, out_dir, "EVENT")

    assert out_tif.exists()
    assert prov.product_id == VERIFIED_EVENT_SCENE_ID
    assert prov.role == "EVENT"
    assert prov.crs == "EPSG:32643"
    assert prov.resolution_m == 10.0
    assert prov.nodata_value == -9999.0

    # Reopen with rasterio and check bounds, shape, nodata, crs
    with rasterio.open(out_tif) as src:
        assert src.crs.to_string() == "EPSG:32643"
        assert src.width == 2220
        assert src.height == 4320
        assert src.nodata == -9999.0
        assert src.bounds.left == 512700.0
        assert src.bounds.bottom == 1955900.0
        assert src.bounds.right == 534900.0
        assert src.bounds.top == 1999100.0


def test_wrong_package_name_rejection(tmp_path):
    wrong_zip = tmp_path / "S1A_IW_GRDH_WRONG_SCENE.zip"
    wrong_zip.write_bytes(b"dummy")

    out_dir = tmp_path / "processed"
    with pytest.raises(ValueError, match="Mismatched product ID"):
        process_authentic_sentinel1_package(wrong_zip, out_dir, "EVENT")


def test_live_earth_engine_status_blocked_without_auth():
    service = EarthEngineService()
    assert service.initialized is False
    assert service.auth_error is not None
