from datetime import UTC, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel
from pyproj import Transformer

CUSEC_TO_M3S_FACTOR = 0.028316846592
M3S_TO_CUSEC_FACTOR = 35.314666721489
IST_OFFSET_HOURS = 5.5


def cusecs_to_m3s(cusecs: float) -> float:
    """Convert flow in cubic feet per second (cusecs) to cubic metres per second (m3/s)."""
    if cusecs < 0:
        raise ValueError("Discharge rate cannot be negative")
    return round(cusecs * CUSEC_TO_M3S_FACTOR, 4)


def m3s_to_cusecs(m3s: float) -> float:
    """Convert flow in cubic metres per second (m3/s) to cusecs."""
    if m3s < 0:
        raise ValueError("Discharge rate cannot be negative")
    return round(m3s * M3S_TO_CUSEC_FACTOR, 2)


def ist_to_utc(ist_dt_str: str) -> str:
    """Convert Indian Standard Time (IST, UTC+5:30) datetime string to UTC ISO-8601 string."""
    clean_str = ist_dt_str.replace("Z", "").split("+")[0]
    dt = datetime.fromisoformat(clean_str)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.replace(tzinfo=ist_tz)
    dt_utc = dt_ist.astimezone(UTC)
    return dt_utc.isoformat().replace("+00:00", "Z")


class ChannelApproximationResult(BaseModel):
    method: Literal["TERRAIN_ONLY_CHANNEL_APPROXIMATION"] = "TERRAIN_ONLY_CHANNEL_APPROXIMATION"
    bankfull_width_m: float = 120.0
    estimated_bed_depth_m: float = 3.5
    manning_roughness_n: float = 0.035
    notes: str = (
        "TERRAIN-ONLY CHANNEL APPROXIMATION: Bed level deepened below DEM water surface by estimated "
        "3.5m bankfull depth. This approximation carries hydraulic uncertainty and must not be treated as surveyed bathymetry."
    )


class DEMMetadata(BaseModel):
    provider: str = "Copernicus / ESA / JAXA"
    product_name: str = "Copernicus DEM GLO-30 (30m)"
    horizontal_resolution_m: float = 30.0
    native_crs: str = "EPSG:4326"
    vertical_datum: str = "EGM96"
    nodata_value: float = -9999.0
    licence: str = "Copernicus Open Access"
    source_url: str = "https://registry.opendata.aws/copernicus-dem/"
    coverage_wgs84: tuple[float, float, float, float] = (74.60, 17.65, 75.95, 18.35)
    quality_notes: str = "Void-filled 30m DEM covering Ujjani reservoir and entire Bhima river reach to Pandharpur."


def project_wgs84_to_utm43n(lon: float, lat: float) -> tuple[float, float]:
    """Transform WGS84 coordinate (lon, lat) to UTM Zone 43N projected coordinate (Easting, Northing)."""
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    easting, northing = transformer.transform(lon, lat)
    return round(easting, 2), round(northing, 2)


def project_utm43n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Transform UTM Zone 43N coordinate (Easting, Northing) to WGS84 (lon, lat)."""
    transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return round(lon, 6), round(lat, 6)
