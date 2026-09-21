"""Tests for Phase 5C Sentinel-1 Bitemporal Flood Classification."""

import numpy as np
import pytest
import rasterio
from damsafe.observation.flood_classifier import (
    CLASS_EVENT_FLOOD,
    CLASS_NODATA,
    CLASS_NOT_FLOODED,
    CLASS_PERMANENT_WATER,
    classify_sentinel1_flood,
    generate_flood_mask_geotiff,
)
from damsafe.observation.sar_processor import create_standard_aligned_geotiff
from damsafe.observation.sentinel1_retrieval import (
    UJJANI_MODEL_GRID_NODATA,
)


def test_flood_classification_classes_and_permanent_water_exclusion():
    # 4x4 test grid
    # Pixel (0,0): Pre=-10 (land), Event=-16 (water, drop=-6dB) -> EVENT_FLOOD (1)
    # Pixel (0,1): Pre=-18 (water), Event=-18 (water, drop=0dB) -> PERMANENT_WATER (2)
    # Pixel (0,2): Pre=-10 (land), Event=-10 (land, drop=0dB) -> NOT_FLOODED (0)
    # Pixel (0,3): Pre=-9999 (nodata), Event=-10 -> NODATA (-1)
    pre = np.array([
        [-10.0, -18.0, -10.0, -9999.0],
        [-10.0, -18.0, -10.0, -10.0],
        [-10.0, -10.0, -10.0, -10.0],
        [-10.0, -10.0, -10.0, -10.0],
    ], dtype=np.float32)

    ev = np.array([
        [-16.0, -18.0, -10.0, -10.0],
        [-16.0, -18.0, -10.0, -10.0],
        [-16.0, -10.0, -10.0, -10.0],
        [-16.0, -10.0, -10.0, -10.0],
    ], dtype=np.float32)

    classified = classify_sentinel1_flood(
        ev, pre,
        vv_flood_threshold_db=-14.0,
        vv_change_threshold_db=-3.0,
        perm_water_threshold_db=-15.0,
        nodata_val=-9999.0,
        apply_speckle_filter=False,
    )

    # Class codes verification
    assert classified[0, 0] == CLASS_EVENT_FLOOD
    assert classified[0, 1] == CLASS_PERMANENT_WATER
    assert classified[0, 2] == CLASS_NOT_FLOODED
    assert classified[0, 3] == CLASS_NODATA

    # Ensure permanent water is never marked as event flood
    perm_mask = (pre <= -15.0) & (ev <= -15.0)
    assert np.all(classified[perm_mask] == CLASS_PERMANENT_WATER)
    assert not np.any(classified[perm_mask] == CLASS_EVENT_FLOOD)


def test_nodata_preservation():
    pre = np.full((10, 10), UJJANI_MODEL_GRID_NODATA, dtype=np.float32)
    ev = np.full((10, 10), -16.0, dtype=np.float32)

    classified = classify_sentinel1_flood(ev, pre, nodata_val=UJJANI_MODEL_GRID_NODATA)
    assert np.all(classified == CLASS_NODATA)


def test_deterministic_classification():
    pre = np.random.uniform(-25.0, -5.0, size=(50, 50)).astype(np.float32)
    ev = np.random.uniform(-25.0, -5.0, size=(50, 50)).astype(np.float32)

    c1 = classify_sentinel1_flood(ev, pre)
    c2 = classify_sentinel1_flood(ev, pre)
    assert np.array_equal(c1, c2)


def test_shape_mismatch_rejection():
    pre = np.zeros((10, 10), dtype=np.float32)
    ev = np.zeros((10, 12), dtype=np.float32)

    with pytest.raises(ValueError, match="Shape mismatch"):
        classify_sentinel1_flood(ev, pre)


def test_generate_flood_mask_geotiff_end_to_end(tmp_path):
    # Create valid synthetic event & preevent GeoTIFFs
    data_pre = np.full((100, 100), -10.0, dtype=np.float32)
    data_pre[10:30, 10:30] = -18.0  # Permanent water pool
    data_ev = np.full((100, 100), -10.0, dtype=np.float32)
    data_ev[10:30, 10:30] = -18.0   # Permanent water pool
    data_ev[40:60, 40:60] = -16.0   # New flooded zone

    ev_path = tmp_path / "ev.tif"
    pre_path = tmp_path / "pre.tif"
    out_mask = tmp_path / "mask.tif"

    create_standard_aligned_geotiff(ev_path, data_ev)
    create_standard_aligned_geotiff(pre_path, data_pre)

    out_file, prov = generate_flood_mask_geotiff(ev_path, pre_path, out_mask)
    assert out_file.exists()
    assert prov["crs"] == "EPSG:32643"
    assert prov["pixel_counts"]["PERMANENT_WATER"] > 0
    assert prov["pixel_counts"]["EVENT_FLOOD"] > 0

    with rasterio.open(out_file) as src:
        assert src.crs.to_string() == "EPSG:32643"
        assert src.nodata == CLASS_NODATA
        assert src.tags().get("damsafe_product") == "UJJANI_OBSERVED_FLOOD_MASK"
