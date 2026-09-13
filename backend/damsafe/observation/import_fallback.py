from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field
from damsafe.observation.gee import SARProcessingConfig, Sentinel1Scene, SatelliteObservation, ObservationMode, ObservationState


class ImportedObservationInput(BaseModel):
    site_key: str = Field(min_length=1, max_length=60)
    provider_agency: str = Field(min_length=1, max_length=200)
    ee_dataset_collection: str = Field(min_length=1, max_length=200)
    scene_ids: tuple[str, ...] = Field(min_length=1)
    acquisition_time: str = Field(min_length=1)
    orbit_direction: Literal["ASCENDING", "DESCENDING"] = "DESCENDING"
    relative_orbit: int = Field(gt=0)
    crs: str = "EPSG:4326"
    resolution_m: float = Field(gt=0)
    processing_method: str = Field(min_length=1)
    threshold_db: float
    permanent_water_treatment: str = Field(min_length=1)
    quality_mask_treatment: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    bounds_wgs84: tuple[float, float, float, float]
    matrix: list[list[int]]


def import_authentic_observation(data: ImportedObservationInput) -> SatelliteObservation:
    proc_time = datetime.now(timezone.utc).isoformat()

    scene = Sentinel1Scene(
        scene_id=",".join(data.scene_ids),
        acquisition_time=data.acquisition_time,
        orbit_direction=data.orbit_direction,
        relative_orbit=data.relative_orbit,
        instrument_mode="IW",
        polarization="VV+VH",
        footprint_wgs84=data.bounds_wgs84,
        collection=data.ee_dataset_collection,
        preprocessing_timestamp=proc_time,
    )

    config = SARProcessingConfig(
        speckle_filter=data.processing_method,
        backscatter_domain="dB",
        flood_threshold_db=data.threshold_db,
        permanent_water_mask_source=data.permanent_water_treatment,
        terrain_mask_source=data.quality_mask_treatment,
    )

    rows = len(data.matrix)
    cols = len(data.matrix[0]) if rows > 0 else 0
    counts = {"FLOODED": 0, "NOT_FLOODED": 0, "PERMANENT_WATER": 0, "UNRELIABLE": 0, "NODATA": 0}

    w, s, e, n = data.bounds_wgs84
    dx = (e - w) / cols if cols > 0 else 0.001
    dy = (n - s) / rows if rows > 0 else 0.001
    cell_area_km2 = (dx * 111.0) * (dy * 111.0)

    for row in data.matrix:
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

    total_cells = rows * cols
    valid_cells = total_cells - counts["NODATA"]
    valid_coverage_pct = (valid_cells / total_cells) * 100.0 if total_cells > 0 else 0.0

    flooded_area = counts["FLOODED"] * cell_area_km2
    perm_water_area = counts["PERMANENT_WATER"] * cell_area_km2

    return SatelliteObservation(
        observation_id=f"obs-import-{data.site_key}-{data.acquisition_time[:10]}",
        site_key=data.site_key,
        mode=ObservationMode.HISTORICAL_EVENT,
        provenance_type="AUTHENTIC_IMPORTED_OBSERVATION",
        execution_state=ObservationState.PASS,
        scene_info=scene,
        processing_config=config,
        acquisition_time=data.acquisition_time,
        processing_timestamp=proc_time,
        grid_bounds_wgs84=data.bounds_wgs84,
        width=cols,
        height=rows,
        flooded_area_km2=round(flooded_area, 2),
        permanent_water_area_km2=round(perm_water_area, 2),
        valid_coverage_pct=round(valid_coverage_pct, 1),
        pixel_counts=counts,
        grid_matrix=data.matrix,
        notes=f"Authentic external Sentinel-1 observation imported. Provider: {data.provider_agency}. Licence: {data.licence}.",
    )
