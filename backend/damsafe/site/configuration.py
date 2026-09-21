"""Generic Site Configuration contract and registry.

Decouples site-specific geographic and hydraulic data (such as Ujjani Dam and the Bhima reach)
from core solver execution and scenario routing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .ujjani import BHIMA_REACH, UJJANI_DAM_SPECS


class SiteIdentity(BaseModel):
    site_key: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    site_name: str = Field(min_length=1, max_length=120)
    river_name: str = Field(min_length=1, max_length=120)
    basin_name: str = ""
    state: str = ""
    country: str = "India"
    description: str = ""


class SiteSpatial(BaseModel):
    bounds_wgs84: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    computation_crs: str  # e.g. "EPSG:32643"
    vertical_reference: str = "EGM96"
    river_centerline_wgs84: tuple[tuple[float, float], ...]  # (lon, lat) points
    approximate_reach_length_km: float = 115.0

    @field_validator("bounds_wgs84")
    @classmethod
    def validate_bounds(cls, v: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        w, s, e, n = v
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise ValueError("Invalid WGS84 bounding box coordinates")
        return v

    @field_validator("river_centerline_wgs84")
    @classmethod
    def validate_centerline(cls, v: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
        if len(v) < 2:
            raise ValueError("Centerline requires at least 2 points (upstream and downstream)")
        return v


class SiteTerrain(BaseModel):
    dem_dataset_id: str | None = None
    bathymetry_dataset_id: str | None = None
    terrain_mode: Literal["TERRAIN_BASED", "SYNTHETIC_BENCHMARK"] = "TERRAIN_BASED"
    dem_paths: list[Path] | None = None
    domain_width_m: float = 2000.0
    channel_width_m: float = 300.0
    channel_bankfull_depth_m: float = 3.0
    n_stream: int = 20
    n_cross: int = 4


class SiteHydraulic(BaseModel):
    roughness_channel_manning: float = 0.035
    roughness_floodplain_manning: float = 0.055
    initial_water_depth_m: float = 0.5
    downstream_stage_m: float = 443.2
    default_baseflow_m3s: float = 150.0
    default_peak_release_m3s: float = 7079.2


class SiteStructure(BaseModel):
    structure_type: Literal["DAM", "NATURAL_BLOCKAGE", "NONE"] = "DAM"
    name: str = ""
    latitude_deg: float = 18.0772
    longitude_deg: float = 75.1197
    crest_elevation_m: float = 497.0
    dam_height_m: float = 56.4
    deepest_foundation_level_m: float = 440.6
    crest_length_m: float = 2534.0
    full_reservoir_level_m: float = 496.83
    maximum_water_level_m: float = 497.58
    minimum_drawdown_level_m: float = 491.03
    gross_storage_capacity_m3: float = 3_140_000_000.0  # 117.24 TMC
    live_storage_capacity_m3: float = 1_517_000_000.0   # 53.57 TMC
    dead_storage_capacity_m3: float = 1_623_000_000.0   # 63.67 TMC
    spillway_type: str = "Ogee crest with radial gates"
    gate_count: int = 41
    # Natural blockage properties (for landslide / river blockage scenarios)
    blockage_height_m: float | None = None
    impounded_lake_volume_m3: float | None = None


class SiteConfiguration(BaseModel):
    """Generic specification representing any river reach or dam site for hydrodynamic simulation."""
    identity: SiteIdentity
    spatial: SiteSpatial
    terrain: SiteTerrain = Field(default_factory=SiteTerrain)
    hydraulic: SiteHydraulic = Field(default_factory=SiteHydraulic)
    structure: SiteStructure = Field(default_factory=SiteStructure)


def get_ujjani_site_configuration() -> SiteConfiguration:
    """Instantiate the authoritative Ujjani Dam & Bhima River reach preset."""
    return SiteConfiguration(
        identity=SiteIdentity(
            site_key="ujjani-bhima",
            site_name=UJJANI_DAM_SPECS.name,
            river_name=BHIMA_REACH.river_name,
            basin_name="Krishna Basin",
            state=UJJANI_DAM_SPECS.state,
            country="India",
            description="Ujjani Dam on the Bhima River downstream to Pandharpur.",
        ),
        spatial=SiteSpatial(
            bounds_wgs84=BHIMA_REACH.bounding_box_wgs84,
            computation_crs=BHIMA_REACH.projected_modelling_crs,
            vertical_reference=BHIMA_REACH.vertical_reference,
            river_centerline_wgs84=BHIMA_REACH.key_centerline_coords_wgs84,
            approximate_reach_length_km=BHIMA_REACH.approximate_reach_length_km,
        ),
        terrain=SiteTerrain(
            terrain_mode="TERRAIN_BASED",
            domain_width_m=2000.0,
            channel_width_m=300.0,
            channel_bankfull_depth_m=3.0,
            n_stream=20,
            n_cross=4,
        ),
        hydraulic=SiteHydraulic(
            roughness_channel_manning=0.035,
            roughness_floodplain_manning=0.055,
            downstream_stage_m=443.2,
            default_baseflow_m3s=150.0,
            default_peak_release_m3s=7079.2,
        ),
        structure=SiteStructure(
            structure_type="DAM",
            name=UJJANI_DAM_SPECS.name,
            latitude_deg=UJJANI_DAM_SPECS.latitude_deg,
            longitude_deg=UJJANI_DAM_SPECS.longitude_deg,
            crest_elevation_m=UJJANI_DAM_SPECS.crest_elevation_m,
            dam_height_m=UJJANI_DAM_SPECS.dam_height_m,
            deepest_foundation_level_m=UJJANI_DAM_SPECS.deepest_foundation_level_m,
            crest_length_m=UJJANI_DAM_SPECS.crest_length_total_m,
            full_reservoir_level_m=UJJANI_DAM_SPECS.full_reservoir_level_m,
            maximum_water_level_m=UJJANI_DAM_SPECS.maximum_water_level_m,
            minimum_drawdown_level_m=UJJANI_DAM_SPECS.minimum_drawdown_level_m,
            gross_storage_capacity_m3=UJJANI_DAM_SPECS.gross_storage_capacity_m3,
            live_storage_capacity_m3=UJJANI_DAM_SPECS.live_storage_capacity_m3,
            dead_storage_capacity_m3=UJJANI_DAM_SPECS.dead_storage_capacity_m3,
            spillway_type=UJJANI_DAM_SPECS.spillway_type,
            gate_count=UJJANI_DAM_SPECS.gate_count,
        ),
    )


# Registry of verified site presets
SITE_PRESETS: dict[str, SiteConfiguration] = {
    "ujjani-bhima": get_ujjani_site_configuration(),
}


def load_site_configuration(site_key: str, project_dict: dict[str, Any] | None = None) -> SiteConfiguration:
    """Resolve a SiteConfiguration by site_key or from project metadata."""
    if site_key in SITE_PRESETS:
        preset = SITE_PRESETS[site_key]
        if project_dict and project_dict.get("verified_bounds_wgs84"):
            # Allow project override of bounds or CRS if specified
            b = project_dict["verified_bounds_wgs84"]
            crs = project_dict.get("computation_crs") or preset.spatial.computation_crs
            vref = project_dict.get("vertical_reference") or preset.spatial.vertical_reference
            spatial = preset.spatial.model_copy(update={
                "bounds_wgs84": tuple(b),
                "computation_crs": crs,
                "vertical_reference": vref,
            })
            return preset.model_copy(update={"spatial": spatial})
        return preset

    # Generic configuration synthesized from project record
    if project_dict:
        bounds = project_dict.get("verified_bounds_wgs84") or (74.60, 17.65, 75.95, 18.35)
        crs = project_dict.get("computation_crs") or "EPSG:32643"
        vref = project_dict.get("vertical_reference") or "EGM96"
        return SiteConfiguration(
            identity=SiteIdentity(
                site_key=site_key,
                site_name=project_dict.get("name", site_key),
                river_name=project_dict.get("name", "Generic River"),
            ),
            spatial=SiteSpatial(
                bounds_wgs84=tuple(bounds),
                computation_crs=crs,
                vertical_reference=vref,
                river_centerline_wgs84=BHIMA_REACH.key_centerline_coords_wgs84,
            ),
        )

    raise ValueError(f"Unknown site configuration key: {site_key}")
