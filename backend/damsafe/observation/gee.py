import os
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

try:
    import ee  # type: ignore
    HAS_EE = True
except ImportError:
    HAS_EE = False


class ObservationMode(StrEnum):
    HISTORICAL_EVENT = "HISTORICAL_EVENT"
    LATEST_AVAILABLE = "LATEST_AVAILABLE"


class ObservationState(StrEnum):
    UNCONFIGURED = "UNCONFIGURED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHENTICATED = "AUTHENTICATED"
    SCENE_DISCOVERED = "SCENE_DISCOVERED"
    NO_SUITABLE_SCENE = "NO_SUITABLE_SCENE"
    PROCESSING = "PROCESSING"
    OBSERVATION_READY = "OBSERVATION_READY"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    SYNTHETIC_TEST_DATA = "SYNTHETIC_TEST_DATA"


class Sentinel1Scene(BaseModel):
    scene_id: str
    acquisition_time: str
    orbit_direction: Literal["ASCENDING", "DESCENDING"]
    relative_orbit: int
    instrument_mode: str = "IW"
    polarization: str = "VV+VH"
    footprint_wgs84: tuple[float, float, float, float]
    collection: str = "COPERNICUS/S1_GRD"
    preprocessing_timestamp: str
    pass_type: str = "DESCENDING"
    processing_version: str = "1.0.0"


class SARProcessingConfig(BaseModel):
    speckle_filter: str = "Refined_Lee_3x3"
    backscatter_domain: str = "dB"
    flood_threshold_db: float = -14.0
    change_threshold_db: float = -3.0
    slope_threshold_deg: float = 5.0
    permanent_water_mask_source: str = "JRC_GSW_v1_4_Seasonality"
    terrain_mask_source: str = "SRTM_DEM_Slope_HAND"


class SatelliteObservation(BaseModel):
    observation_id: str
    site_key: str
    mode: ObservationMode
    provenance_type: Literal[
        "LIVE_EARTH_ENGINE_RESULT",
        "AUTHENTIC_IMPORTED_OBSERVATION",
        "SYNTHETIC_TEST_DATA",
    ]
    execution_state: ObservationState
    scene_info: Sentinel1Scene | None = None
    processing_config: SARProcessingConfig = Field(default_factory=SARProcessingConfig)
    acquisition_time: str | None = None
    processing_timestamp: str
    grid_bounds_wgs84: tuple[float, float, float, float]
    width: int = 0
    height: int = 0
    flooded_area_km2: float = 0.0
    permanent_water_area_km2: float = 0.0
    valid_coverage_pct: float = 0.0
    pixel_counts: dict[str, int] = Field(default_factory=dict)
    grid_matrix: list[list[int]] | None = None
    notes: str = ""


class EarthEngineService:
    def __init__(self) -> None:
        self.project_id = os.getenv("EE_PROJECT", "")
        self.service_account = os.getenv("EE_SERVICE_ACCOUNT_JSON", "")
        self.initialized = False
        self.auth_error: str | None = None
        self._try_initialize()

    def _try_initialize(self) -> None:
        if not HAS_EE:
            self.auth_error = "google-earth-engine Python package 'ee' is not installed."
            return
        if not self.project_id:
            self.auth_error = "EE_PROJECT environment variable is not set."
            return
        try:
            if self.service_account:
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account,
                    scopes=["https://www.googleapis.com/auth/earthengine",
                            "https://www.googleapis.com/auth/cloud-platform"],
                )
                ee.Initialize(credentials=credentials, project=self.project_id)
            else:
                ee.Initialize(project=self.project_id)
            self.initialized = True
        except Exception:  # noqa: BLE001 -- provider errors may contain credential material
            self.auth_error = "Earth Engine authentication failed. Check project access and local credentials."

    def get_readiness_state(self) -> ObservationState:
        """Return the current authentication readiness state of Earth Engine."""
        if not HAS_EE or not self.project_id:
            return ObservationState.UNCONFIGURED
        if not self.initialized:
            return ObservationState.AUTHENTICATION_FAILED
        return ObservationState.AUTHENTICATED

    def query_sentinel1(
        self,
        site_key: str,
        bounds_wgs84: tuple[float, float, float, float],
        mode: ObservationMode,
        target_time: str | None = None,
        config: SARProcessingConfig | None = None,
        orbit_direction: Literal["ASCENDING", "DESCENDING"] = "DESCENDING",
        polarization: str = "VV+VH",
    ) -> SatelliteObservation:
        config = config or SARProcessingConfig()
        proc_time = datetime.now(UTC).isoformat()

        # 1. If Earth Engine is NOT initialized, check for authentic local processed data
        if not self.initialized:
            # A filename alone cannot establish authentic scene provenance.
            # Use the explicit attributed import endpoint for exported observations.

            # Otherwise return unconfigured/authentication failed with DATA_REQUIRED notice
            state = ObservationState.UNCONFIGURED if not self.project_id else ObservationState.AUTHENTICATION_FAILED
            return SatelliteObservation(
                observation_id=f"obs-{site_key}-unconfigured",
                site_key=site_key,
                mode=mode,
                provenance_type="LIVE_EARTH_ENGINE_RESULT",
                execution_state=state,
                scene_info=None,
                processing_config=config,
                acquisition_time=target_time,
                processing_timestamp=proc_time,
                grid_bounds_wgs84=bounds_wgs84,
                width=0,
                height=0,
                flooded_area_km2=0.0,
                permanent_water_area_km2=0.0,
                valid_coverage_pct=0.0,
                pixel_counts={},
                grid_matrix=None,
                notes=(
                    f"DATA_REQUIRED: Earth Engine is {state} ({self.auth_error}). "
                    "No synthetic observation is substituted. Authentic Copernicus credentials or local verified GeoTIFF required."
                ),
            )

        # 2. Live Earth Engine execution when authenticated
        try:
            aoi = ee.Geometry.Rectangle(list(bounds_wgs84))
            s1_col = (
                ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(aoi)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
                .filter(ee.Filter.eq("orbitProperties_pass", orbit_direction))
            )

            if mode == ObservationMode.HISTORICAL_EVENT and target_time:
                # Date range window around target_time (+/- 1 day)
                target_dt = datetime.fromisoformat(target_time)
                date_start = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                date_end = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                s1_col = s1_col.filterDate(date_start, date_end)
            else:
                # Latest overpass within last 30 days
                now = datetime.now(UTC)
                date_end = now.strftime("%Y-%m-%d")
                date_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                s1_col = s1_col.filterDate(date_start, date_end).sort("system:time_start", False)

            count = s1_col.size().getInfo()
            if count == 0:
                return SatelliteObservation(
                    observation_id=f"obs-{site_key}-no-scene",
                    site_key=site_key,
                    mode=mode,
                    provenance_type="LIVE_EARTH_ENGINE_RESULT",
                    execution_state=ObservationState.NO_SUITABLE_SCENE,
                    scene_info=None,
                    processing_config=config,
                    acquisition_time=target_time,
                    processing_timestamp=proc_time,
                    grid_bounds_wgs84=bounds_wgs84,
                    width=0,
                    height=0,
                    flooded_area_km2=0.0,
                    permanent_water_area_km2=0.0,
                    valid_coverage_pct=0.0,
                    pixel_counts={},
                    grid_matrix=None,
                    notes="NO_SUITABLE_SCENE: No Sentinel-1 IW GRD scene found matching AOI, acquisition date, orbit, and polarization filters.",
                )

            # Retrieve top matching image metadata
            image = s1_col.first()
            props = image.getInfo()["properties"]
            scene_id = props.get("system:index", "UNKNOWN_S1_SCENE")
            time_start_ms = props.get("system:time_start", 0)
            acq_dt = datetime.fromtimestamp(time_start_ms / 1000.0, tz=UTC).isoformat()
            rel_orbit = props.get("relativeOrbitNumber_start", 0)

            scene = Sentinel1Scene(
                scene_id=scene_id,
                acquisition_time=acq_dt,
                orbit_direction=orbit_direction,
                relative_orbit=rel_orbit,
                instrument_mode="IW",
                polarization=polarization,
                footprint_wgs84=bounds_wgs84,
                collection="COPERNICUS/S1_GRD",
                preprocessing_timestamp=proc_time,
                pass_type=orbit_direction,
                processing_version="1.0.0",
            )

            # Return SCENE_DISCOVERED (raster is not yet downloaded/processed into OBSERVATION_READY)
            return SatelliteObservation(
                observation_id=f"obs-{site_key}-{scene_id[:20]}",
                site_key=site_key,
                mode=mode,
                provenance_type="LIVE_EARTH_ENGINE_RESULT",
                execution_state=ObservationState.SCENE_DISCOVERED,
                scene_info=scene,
                processing_config=config,
                acquisition_time=acq_dt,
                processing_timestamp=proc_time,
                grid_bounds_wgs84=bounds_wgs84,
                width=0,
                height=0,
                flooded_area_km2=0.0,
                permanent_water_area_km2=0.0,
                valid_coverage_pct=0.0,
                pixel_counts={},
                grid_matrix=None,
                notes=f"Discovered authentic Sentinel-1 scene '{scene_id}' via Google Earth Engine API. Scene discovered; full raster download and flood classification required for OBSERVATION_READY.",
            )

        except Exception:  # noqa: BLE001 -- redact provider responses and preserve explicit failure state
            return SatelliteObservation(
                observation_id=f"obs-{site_key}-failed",
                site_key=site_key,
                mode=mode,
                provenance_type="LIVE_EARTH_ENGINE_RESULT",
                execution_state=ObservationState.PROCESSING_FAILED,
                scene_info=None,
                processing_config=config,
                acquisition_time=target_time,
                processing_timestamp=proc_time,
                grid_bounds_wgs84=bounds_wgs84,
                width=0,
                height=0,
                flooded_area_km2=0.0,
                permanent_water_area_km2=0.0,
                valid_coverage_pct=0.0,
                pixel_counts={},
                grid_matrix=None,
                notes="PROCESSING_FAILED: Earth Engine query failed. Check authentication, project permissions and requested dates.",
            )


def create_synthetic_test_observation(
    site_key: str = "ujjani-test",
    matrix: list[list[int]] | None = None,
    bounds_wgs84: tuple[float, float, float, float] = (74.6, 18.0, 75.1, 18.4),
    acquisition_time: str = "2020-08-15T10:30:00Z",
) -> SatelliteObservation:
    """Explicitly isolated test-only helper generating SYNTHETIC_TEST_DATA for unit tests."""
    matrix = matrix or [[0, 1], [2, 3]]
    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0
    proc_time = datetime.now(UTC).isoformat()

    counts = {"FLOODED": 0, "NOT_FLOODED": 0, "PERMANENT_WATER": 0, "UNRELIABLE": 0, "NODATA": 0}
    for row in matrix:
        for val in row:
            if val == 1:
                counts["FLOODED"] += 1
            elif val == 0:
                counts["NOT_FLOODED"] += 1
            elif val == 2:
                counts["PERMANENT_WATER"] += 1
            elif val == 3:
                counts["UNRELIABLE"] += 1
            else:
                counts["NODATA"] += 1

    scene = Sentinel1Scene(
        scene_id=f"SYNTHETIC_TEST_SCENE_{acquisition_time[:10]}",
        acquisition_time=acquisition_time,
        orbit_direction="DESCENDING",
        relative_orbit=999,
        instrument_mode="IW",
        polarization="VV+VH",
        footprint_wgs84=bounds_wgs84,
        collection="SYNTHETIC_TEST_COLLECTION",
        preprocessing_timestamp=proc_time,
        pass_type="DESCENDING",
        processing_version="TEST_ONLY",
    )

    return SatelliteObservation(
        observation_id=f"test-obs-{site_key}",
        site_key=site_key,
        mode=ObservationMode.HISTORICAL_EVENT,
        provenance_type="SYNTHETIC_TEST_DATA",
        execution_state=ObservationState.SYNTHETIC_TEST_DATA,
        scene_info=scene,
        processing_config=SARProcessingConfig(),
        acquisition_time=acquisition_time,
        processing_timestamp=proc_time,
        grid_bounds_wgs84=bounds_wgs84,
        width=cols,
        height=rows,
        flooded_area_km2=counts["FLOODED"] * 0.1,
        permanent_water_area_km2=counts["PERMANENT_WATER"] * 0.1,
        valid_coverage_pct=100.0,
        pixel_counts=counts,
        grid_matrix=matrix,
        notes="SYNTHETIC_TEST_DATA: Isolated mock observation for automated unit testing only.",
    )


ee_service = EarthEngineService()
