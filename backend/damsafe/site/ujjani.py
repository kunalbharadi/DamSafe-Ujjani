from typing import Literal
from pydantic import BaseModel, Field


class UjjaniDamSpecification(BaseModel):
    name: str = "Ujjani Dam (Bhima Dam)"
    river: str = "Bhima River (Krishna Basin)"
    state: str = "Maharashtra"
    districts: tuple[str, ...] = ("Solapur", "Pune", "Ahmednagar")
    latitude_deg: float = 18.0772
    longitude_deg: float = 75.1197
    crest_elevation_m: float = 497.0
    deepest_foundation_level_m: float = 440.6
    dam_height_m: float = 56.4
    crest_length_total_m: float = 2534.0
    spillway_length_m: float = 662.0
    earth_dam_length_m: float = 1872.0
    spillway_type: str = "Ogee crest with radial gates"
    gate_count: int = 41
    gate_width_m: float = 12.19
    gate_height_m: float = 8.23
    full_reservoir_level_m: float = 496.83
    maximum_water_level_m: float = 497.58
    minimum_drawdown_level_m: float = 491.03
    gross_storage_capacity_m3: float = 3_140_000_000.0  # 3.14 km3 (117.24 TMC)
    live_storage_capacity_m3: float = 1_517_000_000.0   # 1.517 km3 (53.57 TMC)
    dead_storage_capacity_m3: float = 1_623_000_000.0   # 1.623 km3 (63.67 TMC)
    water_spread_area_frl_km2: float = 337.0
    catchment_area_km2: float = 14858.0
    design_flood_discharge_m3_s: float = 18000.0
    source_reference: str = "Water Resources Department, Government of Maharashtra (WRD) & Central Water Commission (CWC)"


class BhimaReachDefinition(BaseModel):
    reach_name: str = "Ujjani Dam to Pandharpur"
    river_name: str = "Bhima River"
    upstream_node: str = "Ujjani Dam Spillway (18.0772°N, 75.1197°E)"
    downstream_node: str = "Pandharpur Bridge / Gauge Reach (17.6778°N, 75.3283°E)"
    approximate_reach_length_km: float = 115.0
    bounding_box_wgs84: tuple[float, float, float, float] = (74.60, 17.65, 75.95, 18.35)
    source_dem_crs: str = "EPSG:4326"
    projected_modelling_crs: str = "EPSG:32643"  # UTM Zone 43N
    vertical_reference: str = "EGM96"
    channel_geometry_type: Literal["VERIFIED_BATHYMETRY", "TERRAIN_ONLY_CHANNEL_APPROXIMATION"] = "TERRAIN_ONLY_CHANNEL_APPROXIMATION"
    key_centerline_coords_wgs84: tuple[tuple[float, float], ...] = (
        (75.1197, 18.0772),  # Ujjani Dam
        (75.1500, 18.0300),  # Downstream meander 1
        (75.2100, 17.9500),  # Reach near Tembhurni
        (75.2600, 17.8200),  # Reach near Karkamb
        (75.3283, 17.6778),  # Pandharpur
    )


UJJANI_DAM_SPECS = UjjaniDamSpecification()
BHIMA_REACH = BhimaReachDefinition()
