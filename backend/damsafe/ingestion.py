import csv
import math
from datetime import UTC, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import fiona
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from shapely.geometry import shape

from .contracts import DatasetInput


def issue(code, message):
    return {"code": code, "message": message}


def read_hydrology(path, spec: DatasetInput):
    opts = spec.hydro
    assert opts is not None
    units = spec.provenance.units
    factors = {"m3/s": 1.0, "cusec": 0.028316846592}
    if units not in factors:
        raise ValueError("Discharge units must explicitly be m3/s or cusec")
    zone = ZoneInfo(opts.source_timezone) if opts.source_timezone else None
    times, missing, flagged, values = [], 0, 0, []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {opts.timestamp_column, opts.value_column, opts.station_column}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing CSV columns: {sorted(required - set(reader.fieldnames or []))}")
        for index, row in enumerate(reader, 2):
            if index > 500_002:
                raise ValueError("CSV exceeds 500,000 records; split into audited time windows")
            if row[opts.station_column] != opts.station_id:
                raise ValueError(f"Station mismatch at row {index}; split multi-station files explicitly")
            try:
                stamp = (
                    datetime.strptime(row[opts.timestamp_column], opts.timestamp_format)  # noqa: DTZ007 -- resolved or rejected below
                    if opts.timestamp_format
                    else datetime.fromisoformat(row[opts.timestamp_column])
                )
                if stamp.tzinfo is None:
                    if zone is None:
                        raise ValueError("Naive timestamp requires verified source_timezone")
                    aware = stamp.replace(tzinfo=zone)
                    if aware.utcoffset() != stamp.replace(tzinfo=zone, fold=1).utcoffset():
                        raise ValueError("Ambiguous/nonexistent local time; use explicit UTC offset")
                    stamp = aware
                times.append(stamp.astimezone(UTC))
                raw = row[opts.value_column]
                if raw is None or raw.strip().lower() in {"", "na", "null", "nan", "-9999"}:
                    missing += 1
                else:
                    val = float(raw) * factors[units]
                    if not math.isfinite(val) or val < 0:
                        raise ValueError("Nonfinite or negative discharge")
                    values.append(val)
                if row.get(opts.flag_column, "") not in opts.accepted_flags:
                    flagged += 1
            except (TypeError, ValueError) as e:
                raise ValueError(f"CSV row {index}: {e}") from e
    if not times:
        raise ValueError("Empty hydrology file")
    unique = sorted(set(times))
    gaps = [
        (b - a).total_seconds()
        for a, b in pairwise(unique)
        if (b - a).total_seconds() != opts.interval_seconds
    ]
    problems = []
    for condition, code, message in [
        (len(times) != len(unique), "duplicates", "Duplicate timestamps require explicit source correction"),
        (times != sorted(times), "unordered", "Source records are not chronological"),
        (missing, "missing_values", f"{missing} missing values; no zero filling or interpolation performed"),
        (flagged, "quality_flags", f"{flagged} records have unaccepted quality flags"),
        (gaps, "time_gaps", f"{len(gaps)} intervals differ from expected cadence"),
        (opts.measurement != "river_outflow", "measurement", "Verify this series is river outflow"),
        (not opts.identity_reference, "station_identity", "Provide evidence for station and release pathway"),
    ]:
        if condition:
            problems.append(issue(code, message))
    return {
        "issues": problems,
        "record_count": len(times),
        "missing_values": missing,
        "flagged": flagged,
        "duplicates": len(times) - len(unique),
        "gap_count": len(gaps),
        "largest_interval_seconds": max(gaps, default=opts.interval_seconds),
        "start_time": unique[0].isoformat(),
        "end_time": unique[-1].isoformat(),
        "source_timezone": opts.source_timezone,
        "source_units": units,
        "normalized_units": "m3/s",
        "conversion_factor": factors[units],
        "minimum_m3_s": min(values, default=None),
        "maximum_m3_s": max(values, default=None),
        "station_id": opts.station_id,
        "measurement": opts.measurement,
        "interpolation": "none",
        "original_preserved": True,
    }


def validate_crs(actual, declared):
    if not actual or not declared:
        raise ValueError("Both embedded and declared horizontal CRS are required")
    a, b = CRS.from_user_input(actual), CRS.from_user_input(declared)
    if not a.equals(b, ignore_axis_order=True):
        raise ValueError("Declared CRS conflicts with embedded CRS; reproject as a new derived version")
    return a


def read_terrain(path, spec):
    with rasterio.open(path) as src:
        if src.driver != "GTiff" or src.count != 1:
            raise ValueError("Terrain must be a single-band GeoTIFF")
        crs = validate_crs(src.crs, spec.provenance.crs)
        if spec.provenance.units != "m":
            raise ValueError("Terrain elevations must be in metres; record conversion as a derived import")
        if src.width * src.height > 100_000_000:
            raise ValueError("Terrain exceeds phase-1 100 million cell limit; clip the domain first")
        invalid = valid = 0
        minimum, maximum = math.inf, -math.inf
        # Fixed windows also bound memory for striped/untiled inputs.
        for y in range(0, src.height, 512):
            for x in range(0, src.width, 512):
                data = src.read(
                    1,
                    masked=True,
                    window=rasterio.windows.Window(x, y, min(512, src.width - x), min(512, src.height - y)),
                )
                vals = data.compressed()
                invalid += data.size - vals.size
                valid += vals.size
                if not np.isfinite(vals).all():
                    raise ValueError("Terrain has unmasked nonfinite values")
                if vals.size:
                    minimum, maximum = min(minimum, float(vals.min())), max(maximum, float(vals.max()))
        if not valid:
            raise ValueError("Terrain is entirely nodata")
        problems = []
        if invalid:
            problems.append(
                issue("terrain_nodata", "Terrain contains nodata; resolve coverage within the chosen domain")
            )
        if not spec.provenance.vertical_reference or spec.provenance.vertical_reference.lower() == "unknown":
            problems.append(
                issue("vertical_reference", "Resolve terrain elevation datum; no conversion performed")
            )
        if spec.terrain_purpose != "hydraulic":
            problems.append(
                issue("drainage_terrain", "Drainage-conditioned terrain cannot serve as hydraulic terrain")
            )
        bounds = Transformer.from_crs(crs, 4326, always_xy=True).transform_bounds(*src.bounds)
        return {
            "issues": problems,
            "crs": crs.to_string(),
            "bounds_wgs84": bounds,
            "width": src.width,
            "height": src.height,
            "resolution": list(src.res),
            "nodata": str(src.nodata),
            "nodata_cells": invalid,
            "minimum_m": minimum,
            "maximum_m": maximum,
        }


def read_vector(path, spec):
    if path.suffix == ".gpkg":
        layers = fiona.listlayers(path)
        if not spec.layer and len(layers) != 1:
            raise ValueError("Multi-layer GeoPackage requires explicit layer selection")
    with fiona.open(path, layer=spec.layer) as src:
        if src.driver not in {"GeoJSON", "GPKG"}:
            raise ValueError("Only GeoJSON and GeoPackage vectors are allowed")
        crs = validate_crs(src.crs_wkt or src.crs, spec.provenance.crs)
        count = 0
        kinds = set()
        for feature in src:
            count += 1
            if count > 200_000:
                raise ValueError("Vector exceeds 200,000 features; clip first")
            if not feature.geometry:
                raise ValueError("Missing geometry")
            geom = shape(feature.geometry)
            if geom.is_empty or not geom.is_valid or not all(math.isfinite(v) for v in geom.bounds):
                raise ValueError("Empty, nonfinite or invalid geometry")
            kinds.add(geom.geom_type)
        if not count:
            raise ValueError("Empty vector dataset")
        bounds = Transformer.from_crs(crs, 4326, always_xy=True).transform_bounds(*src.bounds)
        if not all(math.isfinite(v) for v in bounds):
            raise ValueError("Invalid transformed bounds")
        return {
            "issues": [],
            "feature_count": count,
            "geometry_types": sorted(kinds),
            "crs": crs.to_string(),
            "bounds_wgs84": bounds,
        }


def inspect(path, spec):
    if spec.kind == "hydrology":
        return read_hydrology(path, spec)
    if spec.kind == "terrain":
        return read_terrain(path, spec)
    return read_vector(path, spec)
