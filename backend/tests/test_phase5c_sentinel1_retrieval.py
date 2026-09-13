"""Tests for Phase 5C Task 2: Verified Sentinel-1 Scene Retrieval Configuration."""

import pytest
from damsafe.observation.sentinel1_retrieval import (
    Sentinel1RetrievalConfig,
    get_october_2020_scene_manifest,
    generate_gee_retrieval_script,
)
from damsafe.observation.gee import EarthEngineService, ObservationState


def test_verified_sentinel1_scene_manifest():
    manifest = get_october_2020_scene_manifest()
    # Event scene
    assert manifest["scene_id"] == "S1A_IW_GRDH_1SDV_20201019T005511_20201019T005536_034858_041058_FF6C"
    assert manifest["satellite"] == "Sentinel-1A"
    assert manifest["acquisition_utc"] == "2020-10-19T00:55:11Z"
    assert manifest["orbit_direction"] == "DESCENDING"
    assert manifest["relative_orbit"] == 136
    assert manifest["instrument_mode"] == "IW"
    assert manifest["product_type"] == "GRDH"
    assert manifest["polarization"] == "VV+VH"
    assert manifest["model_reach_intersected"] is True

    # Pre-event scene
    assert manifest["pre_event_scene_id"] == "S1A_IW_GRDH_1SDV_20201007T005514_20201007T005539_034683_040A32_8AFB"
    assert manifest["pre_event_acquisition_utc"] == "2020-10-07T00:55:14Z"
    assert manifest["pre_event_relative_orbit"] == 136
    assert manifest["temporal_gap_days"] == 12

    # Status
    assert manifest["live_earth_engine_status"] == "BLOCKED"
    assert manifest["authentic_artifact_obtained"] is False


def test_live_earth_engine_status_blocked_without_auth():
    service = EarthEngineService()
    assert service.initialized is False
    assert service.auth_error is not None


def test_gee_retrieval_script_syntax():
    script = generate_gee_retrieval_script()
    assert "COPERNICUS/S1_GRD" in script
    assert "136" in script
    assert "2020-10-19" in script
    assert "2020-10-07" in script
    assert "JRC/GSW1_4/GlobalSurfaceWater" in script
    assert "USGS/SRTMGL1_003" in script
