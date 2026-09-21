import json
from pathlib import Path

import netCDF4
import numpy as np
import pytest
import rasterio
from damsafe.numerics.adapters import capabilities, docker_argv
from damsafe.numerics.execution import Limits, execute
from damsafe.site.hydraulic_case import (
    UjjaniApproximateCaseConfig,
    _build_curvilinear_reach_netcdf,
    build_ujjani_approximate_case,
)
from damsafe.site.terrain_sampler import (
    IncompatibleTerrainError,
    MissingTerrainError,
    sample_dem_elevations,
)
from rasterio.transform import from_origin


def create_mock_dem_geotiff(path: Path, base_elevation: float = 500.0, slope_x: float = 0.0, slope_y: float = 0.0) -> Path:
    """Helper to create a well-formed single-band WGS84 GeoTIFF covering the Ujjani-Pandharpur domain."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Domain: 74.5E to 76.0E, 17.5N to 18.5N (100 x 100 pixels)
    width, height = 100, 100
    res = 0.01  # ~1km per pixel in degrees
    transform = from_origin(74.5, 18.5, res, res)

    rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    data = base_elevation + cols * slope_x + rows * slope_y
    data = data.astype(np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    return path


def test_terrain_dem_sampling_and_provenance(tmp_path):
    dem_path = create_mock_dem_geotiff(tmp_path / "mock_dem.tif", base_elevation=480.0)

    # Points in UTM Zone 43N near Ujjani Dam
    xs = np.array([512000.0, 513000.0, 514000.0])
    ys = np.array([1998000.0, 1997000.0, 1996000.0])

    elevs, prov = sample_dem_elevations(
        dem_paths=[dem_path],
        points_x_utm43n=xs,
        points_y_utm43n=ys,
    )

    assert len(elevs) == 3
    assert np.all(np.isfinite(elevs))
    assert np.all(elevs >= 479.0) and np.all(elevs <= 481.0)
    assert prov.source_crs == "EPSG:4326"
    assert prov.projected_crs == "EPSG:32643"
    assert prov.vertical_datum == "EGM96"
    assert "mock_dem.tif" in prov.file_sha256


def test_bilinear_interpolation_continuous_surface(tmp_path):
    """Verifies that bilinear interpolation produces smooth, subpixel-interpolated elevations."""
    # Create DEM with slope in X (10m per degree)
    dem_path = create_mock_dem_geotiff(tmp_path / "sloped_dem.tif", base_elevation=500.0, slope_x=10.0)

    # Points at slightly different fractional offsets in UTM 43N
    xs = np.array([512000.0, 512250.0, 512500.0])
    ys = np.array([1998000.0, 1998000.0, 1998000.0])

    elevs, _ = sample_dem_elevations(
        dem_paths=[dem_path],
        points_x_utm43n=xs,
        points_y_utm43n=ys,
    )
    # The elevations must strictly increase monotonically due to bilinear blending
    assert elevs[0] < elevs[1] < elevs[2]


def test_sensitivity_altering_dem_elevations_changes_mesh_geometry(tmp_path):
    """Proves that changing DEM elevations directly changes the generated computational mesh geometry."""
    dem_a = create_mock_dem_geotiff(tmp_path / "dem_a.tif", base_elevation=460.0)
    dem_b = create_mock_dem_geotiff(tmp_path / "dem_b.tif", base_elevation=520.0)

    config_a = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[dem_a],
        domain_width_m=2000.0,
    )
    config_b = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[dem_b],
        domain_width_m=2000.0,
    )

    nc_a = tmp_path / "mesh_a.nc"
    nc_b = tmp_path / "mesh_b.nc"

    _build_curvilinear_reach_netcdf(nc_a, config_a)
    _build_curvilinear_reach_netcdf(nc_b, config_b)

    with netCDF4.Dataset(nc_a) as ds_a, netCDF4.Dataset(nc_b) as ds_b:
        z_a = ds_a.variables["NetNode_z"][:]
        z_b = ds_b.variables["NetNode_z"][:]

        # The node elevations must be strictly different and reflect the ~60m shift
        diff = z_b - z_a
        assert np.all(diff > 50.0)
        assert np.all(diff < 70.0)


def test_missing_dem_raises_clear_error_without_fallback(tmp_path):
    """Proves that missing DEM causes immediate failure rather than silently using synthetic geometry."""
    config = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[tmp_path / "non_existent_dem.tif"],
    )

    target = tmp_path / "case_fail"
    with pytest.raises(MissingTerrainError, match="Terrain DEM file not found"):
        build_ujjani_approximate_case(target, config)


def test_incompatible_dem_raises_error(tmp_path):
    """Proves that a multi-band or invalid CRS DEM is rejected."""
    bad_dem = tmp_path / "multiband.tif"
    with rasterio.open(
        bad_dem,
        "w",
        driver="GTiff",
        height=50,
        width=50,
        count=3,  # Multi-band
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(74.5, 18.5, 0.01, 0.01),
    ) as dst:
        dst.write(np.zeros((3, 50, 50), dtype=np.float32))

    config = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[bad_dem],
    )
    with pytest.raises(IncompatibleTerrainError, match="single-band"):
        build_ujjani_approximate_case(tmp_path / "bad_case", config)


def test_synthetic_benchmark_mode_explicitly_labelled(tmp_path):
    """Proves that synthetic benchmark mode is cleanly segregated and explicitly labelled."""
    config = UjjaniApproximateCaseConfig(mode="SYNTHETIC_BENCHMARK")
    target = tmp_path / "synthetic_case"
    case_dict = build_ujjani_approximate_case(target, config)

    assert case_dict["case_kind"] == "SYNTHETIC_BENCHMARK"
    assert case_dict["classification"] == "SYNTHETIC_BENCHMARK"
    assert case_dict["dem_provenance"] is None

    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "SYNTHETIC_BENCHMARK"
    assert manifest["dem_provenance"] is None


def test_partial_coverage_dem_raises_error(tmp_path):
    """Proves that a DEM covering only part of the reach raises an error rather than silently failing."""
    dem_18 = Path("data/raw/terrain/Copernicus_DSM_COG_10_N18_00_E075_00_DEM.tif")
    if not dem_18.exists():
        pytest.skip("Copernicus DEM N18 not present locally")

    # Only supply N18 (missing N17 for downstream reach)
    config = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[dem_18],
    )
    with pytest.raises(IncompatibleTerrainError, match="Provided DEMs did not cover"):
        build_ujjani_approximate_case(tmp_path / "partial_case", config)


def test_terrain_based_ujjani_dflowfm_smoke_execution(tmp_path):
    """Execute a small, practical D-Flow FM smoke test with real sampled Copernicus DEM terrain."""
    dem_18 = Path("data/raw/terrain/Copernicus_DSM_COG_10_N18_00_E075_00_DEM.tif")
    dem_17 = Path("data/raw/terrain/Copernicus_DSM_COG_10_N17_00_E075_00_DEM.tif")
    if not dem_18.exists() or not dem_17.exists():
        pytest.skip("Copernicus DEM N18/N17 not present locally")

    cap = capabilities("dflowfm")
    if not cap.get("available"):
        pytest.skip(f"D-Flow FM engine unavailable: {cap.get('reason')}")

    target = tmp_path / "terrain_dflow_run"
    config = UjjaniApproximateCaseConfig(
        mode="TERRAIN_BASED",
        dem_paths=[dem_18, dem_17],
        domain_width_m=2000.0,
        channel_width_m=300.0,
        n_stream=10,
        n_cross=4,
        time_step_max_s=15.0,
        output_interval_s=60.0,
    )

    build_dict = build_ujjani_approximate_case(target, config)
    assert build_dict["case_kind"] == "SITE_SCENARIO"
    assert build_dict["dem_provenance"] is not None
    assert build_dict["dem_provenance"]["vertical_datum"] == "EGM96"

    # Shorten simulation time for smoke test
    mdu_path = target / "dflowfm" / "ujjani_bhima.mdu"
    mdu_text = mdu_path.read_text(encoding="utf-8")
    mdu_text = mdu_text.replace("TStop                             = 777600", "TStop                             = 300")
    mdu_text = mdu_text.replace("MapInterval                       = 3600.0", "MapInterval                       = 60.0")
    mdu_text = mdu_text.replace("HisInterval                       = 3600.0", "HisInterval                       = 60.0")
    mdu_path.write_text(mdu_text, encoding="utf-8")

    # Run D-Flow FM container
    cmd = ["/delft3d/bin/run_dimr.sh", "-m", "dimr_config.xml"]
    limits = Limits(timeout_seconds=90)
    argv = docker_argv(cap["image_id"], target, cmd, limits, f"smoke-terrain-dflow-{tmp_path.name}")
    res = execute(argv, target, target / "solver.log", limits, container_name=f"smoke-terrain-dflow-{tmp_path.name}")

    assert res["state"] == "SUCCEEDED", f"D-Flow FM solver failed: {res.get('error')}"

    # Verify outputs
    map_nc = target / "dflowfm" / "DFM_OUTPUT_ujjani_bhima" / "ujjani_bhima_map.nc"
    assert map_nc.exists()

    with netCDF4.Dataset(map_nc) as ds:
        assert "mesh2d_s1" in ds.variables or "mesh2d_waterdepth" in ds.variables
        # Ensure time dimension progressed
        assert len(ds.dimensions["time"]) >= 2
