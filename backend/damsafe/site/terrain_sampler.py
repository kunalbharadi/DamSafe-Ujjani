import hashlib
from pathlib import Path

import numpy as np
import rasterio
from pydantic import BaseModel, Field
from rasterio.warp import transform as warp_transform


class MissingTerrainError(ValueError):
    """Raised when required terrain DEM file is missing."""


class IncompatibleTerrainError(ValueError):
    """Raised when provided terrain DEM is corrupt, empty, or has incompatible CRS/units/bounds."""


class DEMProvenance(BaseModel):
    dem_source: str = "Copernicus DEM GLO-30"
    resolution_m: float = 30.0
    version: str = "2020_baseline"
    source_crs: str = "EPSG:4326"
    projected_crs: str = "EPSG:32643"
    vertical_datum: str = "EGM96"
    vertical_units: str = "m"
    bounds_wgs84: tuple[float, float, float, float]
    file_sha256: dict[str, str]
    processing_operations: list[str] = Field(
        default_factory=lambda: [
            "validate_single_band_geotiff",
            "verify_epsg4326_crs",
            "coordinate_transform_utm43n_to_wgs84",
            "bilinear_elevation_sampling",
        ]
    )


def compute_sha256(path: Path) -> str:
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _bilinear_sample_raster(src: rasterio.io.DatasetReaderBase, lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    """Perform true 2D bilinear interpolation from a single-band raster at given (lon, lat) coordinates."""
    arr = src.read(1)
    nodata_val = src.nodata
    inv_transform = ~src.transform

    # Compute floating-point column and row coordinates
    cols_f, rows_f = inv_transform * (lons, lats)

    # Adjust for pixel centers at (0.5, 0.5)
    c_grid = cols_f - 0.5
    r_grid = rows_f - 0.5

    c0 = np.floor(c_grid).astype(int)
    r0 = np.floor(r_grid).astype(int)
    c1 = c0 + 1
    r1 = r0 + 1

    # Fractional offsets
    dc = c_grid - c0
    dr = r_grid - r0

    h, w = arr.shape
    out_of_bounds = (c0 < 0) | (c1 >= w) | (r0 < 0) | (r1 >= h)

    c0_clamped = np.clip(c0, 0, w - 1)
    c1_clamped = np.clip(c1, 0, w - 1)
    r0_clamped = np.clip(r0, 0, h - 1)
    r1_clamped = np.clip(r1, 0, h - 1)

    z00 = arr[r0_clamped, c0_clamped].astype(np.float64)
    z01 = arr[r0_clamped, c1_clamped].astype(np.float64)
    z10 = arr[r1_clamped, c0_clamped].astype(np.float64)
    z11 = arr[r1_clamped, c1_clamped].astype(np.float64)

    # Check for nodata and out-of-bounds
    invalid = out_of_bounds | np.isnan(z00) | np.isnan(z01) | np.isnan(z10) | np.isnan(z11) | (z00 < -9000.0) | (z01 < -9000.0) | (z10 < -9000.0) | (z11 < -9000.0)
    if nodata_val is not None:
        invalid |= (z00 == nodata_val) | (z01 == nodata_val) | (z10 == nodata_val) | (z11 == nodata_val)

    sampled = (
        (1.0 - dr) * (1.0 - dc) * z00
        + (1.0 - dr) * dc * z01
        + dr * (1.0 - dc) * z10
        + dr * dc * z11
    )
    sampled[invalid] = np.nan
    return sampled


def sample_dem_elevations(
    dem_paths: list[Path] | Path,
    points_x_utm43n: np.ndarray,
    points_y_utm43n: np.ndarray,
    source_crs: str = "EPSG:4326",
    projected_crs: str = "EPSG:32643",
    vertical_datum: str = "EGM96",
) -> tuple[np.ndarray, DEMProvenance]:
    """Sample authentic terrain elevations from one or more DEM GeoTIFFs at given UTM Zone 43N coordinates.

    Uses true 2D bilinear interpolation to sample continuous ground elevations across DEM grid cells.
    Enforces strict validation on CRS, single-band format, and domain coverage.
    """
    if isinstance(dem_paths, Path | str):
        dem_paths = [Path(dem_paths)]
    else:
        dem_paths = [Path(p) for p in dem_paths]

    if not dem_paths:
        raise MissingTerrainError("No DEM paths provided for terrain sampling")

    for p in dem_paths:
        if not p.exists():
            raise MissingTerrainError(f"Terrain DEM file not found: {p}")

    # Compute hashes
    file_hashes = {p.name: compute_sha256(p) for p in dem_paths}

    # Transform query points from UTM 43N (EPSG:32643) to WGS84 (EPSG:4326)
    lons, lats = warp_transform(projected_crs, source_crs, points_x_utm43n.tolist(), points_y_utm43n.tolist())
    lons = np.array(lons, dtype=np.float64)
    lats = np.array(lats, dtype=np.float64)

    sampled_elevations = np.full(len(points_x_utm43n), np.nan, dtype=np.float64)
    min_lon = float(np.min(lons))
    min_lat = float(np.min(lats))
    max_lon = float(np.max(lons))
    max_lat = float(np.max(lats))

    # Read and sample from available tiles with true bilinear interpolation
    for dem_path in dem_paths:
        with rasterio.open(dem_path) as src:
            if src.count != 1:
                raise IncompatibleTerrainError(f"Terrain DEM must be single-band GeoTIFF, found {src.count} bands in {dem_path}")

            # Check CRS
            if src.crs is None or not (src.crs.to_string() == "EPSG:4326" or "4326" in str(src.crs)):
                raise IncompatibleTerrainError(f"Expected source CRS {source_crs}, got {src.crs} in {dem_path}")

            b = src.bounds
            # Identify which points fall inside this raster tile
            mask = (lons >= b.left) & (lons <= b.right) & (lats >= b.bottom) & (lats <= b.top)
            if not np.any(mask):
                continue

            indices = np.where(mask)[0]
            tile_samples = _bilinear_sample_raster(src, lons[indices], lats[indices])
            sampled_elevations[indices] = tile_samples

    # Verify that all points were covered
    nan_count = int(np.sum(np.isnan(sampled_elevations)))
    if nan_count > 0:
        raise IncompatibleTerrainError(
            f"Provided DEMs did not cover {nan_count}/{len(points_x_utm43n)} computational grid nodes. "
            f"Query bounds: ({min_lon:.4f}E, {min_lat:.4f}N, {max_lon:.4f}E, {max_lat:.4f}N)"
        )

    provenance = DEMProvenance(
        dem_source="Copernicus DEM GLO-30",
        resolution_m=30.0,
        version="2020_baseline",
        source_crs=source_crs,
        projected_crs=projected_crs,
        vertical_datum=vertical_datum,
        vertical_units="m",
        bounds_wgs84=(min_lon, min_lat, max_lon, max_lat),
        file_sha256=file_hashes,
    )

    return sampled_elevations, provenance
