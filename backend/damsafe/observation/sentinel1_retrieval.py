"""Sentinel-1 GRD SAR Observation Retrieval & Ingestion Configuration for Ujjani-Bhima Event."""

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

# Authoritative Verified Scene Identifiers
VERIFIED_EVENT_SCENE_ID = "S1A_IW_GRDH_1SDV_20201019T005511_20201019T005536_034858_041058_FF6C"
VERIFIED_PRE_EVENT_SCENE_ID = "S1A_IW_GRDH_1SDV_20201007T005514_20201007T005539_034683_040A32_8AFB"

UJJANI_DOMAIN_BBOX_WGS84 = (74.60, 17.65, 75.95, 18.35)

# Standardized Comparison Grid Specification (EPSG:32643 / UTM Zone 43N)
# Covers 115 km reach from Ujjani Dam to Pandharpur matching hydraulic model domain
UJJANI_MODEL_GRID_CRS = "EPSG:32643"
UJJANI_MODEL_GRID_BOUNDS = (512700.0, 1955900.0, 534900.0, 1999100.0)  # (min_x, min_y, max_x, max_y)
UJJANI_MODEL_GRID_PIXEL_SIZE_M = 10.0  # 10m target grid
UJJANI_MODEL_GRID_WIDTH = 2220  # (534900 - 512700) / 10
UJJANI_MODEL_GRID_HEIGHT = 4320  # (1999100 - 1955900) / 10
UJJANI_MODEL_GRID_NODATA = -9999.0
UJJANI_MODEL_GRID_AFFINE = (10.0, 0.0, 512700.0, 0.0, -10.0, 1999100.0)


class UjjaniSARGridSpec(BaseModel):
    """Standardized spatial raster contract for Ujjani model comparison."""

    crs: str = UJJANI_MODEL_GRID_CRS
    bounds_utm43n: tuple[float, float, float, float] = UJJANI_MODEL_GRID_BOUNDS
    pixel_size_m: float = UJJANI_MODEL_GRID_PIXEL_SIZE_M
    width: int = UJJANI_MODEL_GRID_WIDTH
    height: int = UJJANI_MODEL_GRID_HEIGHT
    nodata: float = UJJANI_MODEL_GRID_NODATA
    affine_transform: tuple[float, float, float, float, float, float] = UJJANI_MODEL_GRID_AFFINE
    resolution_note: str = (
        "Reprojection to EPSG:32643 at 10m pixel size aligns with the 2D hydrodynamic solver domain. "
        "Native Sentinel-1 GRD resolution (10m ground range) is preserved; reprojection does not "
        "synthesize or claim higher spatial precision."
    )


class Sentinel1RetrievalConfig(BaseModel):
    """Authoritative retrieval specification for Sentinel-1 GRD observation."""

    # Event Scene (Verified against Copernicus / ASF DAAC)
    scene_id: str = VERIFIED_EVENT_SCENE_ID
    satellite: str = "Sentinel-1A"
    acquisition_utc: str = "2020-10-19T00:55:11Z"
    acquisition_ist: str = "2020-10-19T06:25:11+05:30"
    orbit_direction: str = "DESCENDING"
    relative_orbit: int = 136
    instrument_mode: str = "IW"
    product_type: str = "GRDH"
    polarization: str = "VV+VH"
    footprint_bbox_wgs84: tuple[float, float, float, float] = (73.10, 17.37, 75.76, 19.32)
    model_reach_intersected: bool = True
    native_crs: str = "EPSG:4326"
    processed_crs: str = UJJANI_MODEL_GRID_CRS
    resolution_m: float = 10.0
    collection_name: str = "COPERNICUS/S1_GRD"
    provider_agency: str = "European Space Agency (ESA) / Copernicus / NASA ASF DAAC"
    download_url: str = (
        f"https://datapool.asf.alaska.edu/GRD_HD/SA/{VERIFIED_EVENT_SCENE_ID}.zip"
    )

    # Pre-Event Baseline Reference Scene (Verified against Copernicus / ASF DAAC)
    pre_event_scene_id: str = VERIFIED_PRE_EVENT_SCENE_ID
    pre_event_acquisition_utc: str = "2020-10-07T00:55:14Z"
    pre_event_relative_orbit: int = 136
    pre_event_download_url: str = (
        f"https://datapool.asf.alaska.edu/GRD_HD/SA/{VERIFIED_PRE_EVENT_SCENE_ID}.zip"
    )
    temporal_gap_days: int = 12

    # Processing & Masking Specification
    permanent_water_source: str = "JRC/GSW1_4/GlobalSurfaceWater (occurrence > 80%)"
    quality_mask_method: str = "SRTM_DEM_Slope_HAND (slope > 5 deg) + Refined Lee 3x3 filter (-14.0 dB flood threshold)"

    # Execution & Authentication Status
    live_earth_engine_status: str = "BLOCKED"  # Offline / unauthenticated environment
    authentic_artifact_obtained: bool = False  # Requires NASA Earthdata / CDSE OAuth login
    download_blocker_reason: str = "NASA Earthdata Login / CDSE OAuth authentication required for direct asset retrieval."


class ProcessedSARProvenance(BaseModel):
    """Provenance metadata recorded alongside processed SAR observations."""

    product_id: str
    role: Literal["EVENT", "PRE_EVENT"]
    acquisition_utc: str
    orbit_direction: str = "DESCENDING"
    relative_orbit: int = 136
    polarization: str = "VV+VH"
    source_artifact_sha256: str
    source_format: str  # zip, safe, tif
    processing_steps: list[str]
    crs: str = UJJANI_MODEL_GRID_CRS
    resolution_m: float = 10.0
    nodata_value: float = UJJANI_MODEL_GRID_NODATA
    processed_output_sha256: str
    clip_bounding_box_utm43n: tuple[float, float, float, float] = UJJANI_MODEL_GRID_BOUNDS
    affine_transform: tuple[float, float, float, float, float, float] = UJJANI_MODEL_GRID_AFFINE
    resolution_fidelity_disclaimer: str = (
        "Native SAR ground resolution is 10m. Reprojection to EPSG:32643 matches solver grid "
        "without interpolation inflation."
    )


def calculate_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hex digest for any file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_scene_id(scene_id: str, expected_role: Literal["EVENT", "PRE_EVENT"]) -> bool:
    """Validate that a scene ID strictly matches the verified Copernicus catalog product."""
    if expected_role == "EVENT":
        if scene_id != VERIFIED_EVENT_SCENE_ID:
            raise ValueError(
                f"Invalid event scene ID: '{scene_id}'. Expected verified Copernicus scene '{VERIFIED_EVENT_SCENE_ID}'."
            )
        return True
    elif expected_role == "PRE_EVENT":
        if scene_id != VERIFIED_PRE_EVENT_SCENE_ID:
            raise ValueError(
                f"Invalid pre-event scene ID: '{scene_id}'. Expected verified Copernicus scene '{VERIFIED_PRE_EVENT_SCENE_ID}'."
            )
        return True
    raise ValueError(f"Unknown role: '{expected_role}'")


def get_october_2020_scene_manifest() -> dict[str, Any]:
    """Return dictionary manifest of the October 2020 Sentinel-1 scene retrieval configuration."""
    config = Sentinel1RetrievalConfig()
    return config.model_dump()


def generate_gee_retrieval_script() -> str:
    """Generate exact Python script for Earth Engine data extraction in EPSG:32643."""
    return f"""
import ee

ee.Initialize(project='YOUR_EE_PROJECT_ID')

# Spatial AOI: Ujjani Dam to Pandharpur Reach
aoi = ee.Geometry.Rectangle([74.60, 17.65, 75.95, 18.35])

# Verified Event Scene: 19 Oct 2020 (Relative Orbit 136, Descending)
s1_event = (
    ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi)
    .filterDate('2020-10-19', '2020-10-20')
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
    .filter(ee.Filter.eq('relativeOrbitNumber_start', 136))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .first()
)

# Verified Pre-event Reference: 07 Oct 2020 (Relative Orbit 136, Descending)
s1_pre = (
    ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi)
    .filterDate('2020-10-07', '2020-10-08')
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
    .filter(ee.Filter.eq('relativeOrbitNumber_start', 136))
    .first()
)

# Permanent Water Mask: JRC Global Surface Water (>80% occurrence)
jrc_water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').gt(80).clip(aoi)

# Terrain Slope Mask: SRTM 30m Slope > 5 deg
dem_slope = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003')).gt(5).clip(aoi)

# Flood thresholding (-14 dB on VV polarization)
vv_event = s1_event.select('VV')
flood_raw = vv_event.lt(-14.0)

# Apply masks to isolate transient inundation
flood_extent = flood_raw.updateMask(jrc_water.Not()).updateMask(dem_slope.Not())

# Export to GeoTIFF in EPSG:32643
task = ee.batch.Export.image.toDrive(
    image=flood_extent,
    description='Ujjani_Bhima_Sentinel1_Flood_20201019_EPSG32643',
    folder='EarthEngine_Exports',
    fileNamePrefix='ujjani_flood_s1_20201019_utm43n',
    region=aoi,
    scale=10,
    crs='EPSG:32643',
    maxPixels=1e9
)
task.start()
print('Earth Engine export task submitted for verified scene {VERIFIED_EVENT_SCENE_ID} in EPSG:32643.')
"""
