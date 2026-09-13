"""Run-bound, bounded-memory products from normalized solver output."""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import netCDF4
import numpy as np

from .execution import sha256

CELL_BLOCK = 2048
MAX_RESPONSE_CELLS = 2048
MAX_RESPONSE_FRAMES = 32
MAX_PRODUCT_FRAMES = 10000
PRODUCT_SCHEMA = 2


def _array(variable, index):
    return np.ma.asarray(variable[index]).astype(float).filled(np.nan)


def _provenance(ds):
    return json.loads(ds.provenance_json)


def _absolute_start(provenance):
    units = provenance.get("source_time_units")
    if not units or not units.startswith("seconds since "):
        return None
    try:
        origin = datetime.fromisoformat(units.removeprefix("seconds since ").strip())
        if origin.tzinfo is None:
            return None  # an unqualified source clock is not UTC
        return (origin + timedelta(seconds=float(provenance.get("source_initial_time", 0)))).isoformat()
    except ValueError:
        return None


def metadata(source: Path, *, run_id: str, scenario_id: str | None, configuration_hash: str,
             source_run_id: str | None = None, cached: bool = False):
    with netCDF4.Dataset(source) as ds:
        provenance = _provenance(ds)
        engine = provenance.get("engine", {})
        case = provenance.get("case", {})
        first_time = float(ds["time"][0])
        last_time = float(ds["time"][-1])
        return {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "source_run_id": source_run_id or run_id,
            "cached": cached,
            "engine": engine.get("engine"),
            "model_version": engine.get("source_commit"),
            "engine_image_id": engine.get("image_id"),
            "configuration_hash": configuration_hash,
            "input_sha256": case.get("input_sha256"),
            "case_kind": case.get("case_kind"),
            "input_mode": case.get("input_mode"),
            "execution_origin": provenance.get("execution_origin"),
            "units": {name: getattr(ds[name], "units", None) for name in ("h", "eta", "u", "v", "x", "y", "cell_area", "time")},
            "crs": provenance.get("crs"),
            "vertical_datum": provenance.get("vertical_reference"),
            "nodata_value": {"floating": "NaN", "wet": -1, "valid": 0},
            "nodata_encoding": "valid=0, wet=-1, floating fields NaN",
            "start_time": _absolute_start(provenance),
            "source_local_time": case.get("source_local_time"),
            "source_time_units": provenance.get("source_time_units"),
            "simulation_elapsed_seconds": [first_time, last_time],
            "output_frame_count": len(ds.dimensions["time"]),
            "cell_count": len(ds.dimensions["cell"]),
            "wet_threshold_m": float(ds.wet_threshold_m),
            "arrival_precision": "first saved frame at or above threshold; crossing is bracketed only if the immediately preceding valid frame is below threshold",
            "cell_semantics": "D-Flow horizontal face or SPH per-unit-breadth reporting column; inspect case_kind/CRS",
        }


def postprocess(source: Path, destination: Path, *, threshold_m: float, baseline_mask: Path | None = None,
                cancelled=lambda: False, progress=lambda _: None):
    """Stream one output frame and <=2048 cells at a time; write atomically."""
    if threshold_m <= 0 or not math.isfinite(threshold_m):
        raise ValueError("Arrival threshold must be positive and finite")
    if destination.exists():
        raise ValueError("Immutable product already exists")
    with netCDF4.Dataset(source) as src:
        if len(src.dimensions["time"]) > MAX_PRODUCT_FRAMES:
            raise ValueError("Saved result exceeds bounded 10000-frame product limit")
        times = np.asarray(src["time"][:], dtype=float)
        n = len(src.dimensions["cell"])
        if len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError("Invalid saved output times")
        for name, unit in (("time", "s"), ("x", "m"), ("y", "m"),
                           ("cell_area", "m2"), ("h", "m")):
            if getattr(src[name], "units", None) != unit:
                raise ValueError(f"{name}: expected metric normalized units {unit}")
        if n > 2_000_000:
            raise ValueError("Result exceeds bounded product cell limit")
        if baseline_mask is not None:
            raise ValueError("External baseline masks require a separately verified geospatial contract")
        tmp = destination.with_suffix(".tmp.nc")
        if tmp.exists():
            tmp.unlink()
        try:
            with netCDF4.Dataset(tmp, "w", format="NETCDF4") as out:
                out.createDimension("cell", n)
                out.createDimension("time", len(times))
                for name in ("time", "x", "y", "cell_area"):
                    dimensions = src[name].dimensions
                    var = out.createVariable(name, "f8", dimensions)
                    if name == "time":
                        var[:] = times
                    else:
                        for start in range(0, n, CELL_BLOCK):
                            stop = min(n, start + CELL_BLOCK)
                            var[start:stop] = src[name][start:stop]
                    var.units = getattr(src[name], "units", "")
                for name in ("maximum_depth_m", "maximum_velocity_m_s", "flood_duration_s", "arrival_elapsed_s"):
                    out.createVariable(name, "f8", ("cell",), fill_value=np.nan, zlib=True,
                                       chunksizes=(min(n, CELL_BLOCK),))
                for name in ("cell_state", "valid_frame_count"):
                    out.createVariable(name, "i4", ("cell",), zlib=True,
                                       chunksizes=(min(n, CELL_BLOCK),))
                out.createVariable("flooded_area_m2", "f8", ("time",))
                out.createVariable("unknown_area_m2", "f8", ("time",))
                area_series = np.zeros(len(times), dtype=float)
                unknown_area = np.zeros(len(times), dtype=float)
                for start in range(0, n, CELL_BLOCK):
                    stop = min(n, start + CELL_BLOCK)
                    width = stop - start
                    area = np.asarray(src["cell_area"][start:stop], dtype=float)
                    maximum = np.full(width, np.nan)
                    speed_max = np.full(width, np.nan)
                    duration = np.zeros(width)
                    arrival = np.full(width, np.nan)
                    valid_count = np.zeros(width, dtype=np.int32)
                    reached = np.zeros(width, dtype=bool)
                    for i, time in enumerate(times):
                        if cancelled():
                            raise RuntimeError("Numerical postprocessing cancelled")
                        progress({"stage": "postprocessing", "cells_done": start,
                                  "cells_total": n, "frame": i, "frames_total": len(times)})
                        valid = np.asarray(src["valid"][i, start:stop], dtype=bool)
                        h = _array(src["h"], (i, slice(start, stop)))
                        if np.any(~np.isfinite(h[valid])) or np.any(h[valid] < 0):
                            raise ValueError("Corrupt depth in saved solver output")
                        valid_count += valid.astype(np.int32)
                        maximum = np.fmax(maximum, np.where(valid, h, np.nan))
                        wet = valid & (h >= threshold_m)
                        newly = wet & ~reached
                        arrival[newly] = time
                        reached |= wet
                        area_series[i] += float(np.sum(area[wet]))
                        unknown_area[i] += float(np.sum(area[~valid]))
                        if i + 1 < len(times):
                            duration[wet] += times[i + 1] - time  # left-held saved-frame estimate
                        u = _array(src["u"], (i, slice(start, stop)))
                        v = _array(src["v"], (i, slice(start, stop)))
                        known_velocity = valid & (h >= float(src.wet_threshold_m)) & np.isfinite(u) & np.isfinite(v)
                        speed_max = np.fmax(speed_max, np.where(known_velocity, np.hypot(u, v), np.nan))
                    # 0 = NODATA/uncertain, 1 = NOT_REACHED, 2 = REACHED.
                    # Partial coverage without a crossing remains uncertain, never dry/not reached.
                    state = np.where(reached, 2, np.where(valid_count == len(times), 1, 0))
                    out["maximum_depth_m"][start:stop] = maximum
                    out["maximum_velocity_m_s"][start:stop] = speed_max
                    out["flood_duration_s"][start:stop] = np.where(valid_count == len(times), duration, np.nan)
                    out["arrival_elapsed_s"][start:stop] = arrival
                    out["cell_state"][start:stop] = state
                    out["valid_frame_count"][start:stop] = valid_count
                out["flooded_area_m2"][:] = area_series
                out["unknown_area_m2"][:] = unknown_area
                out.schema_version = PRODUCT_SCHEMA
                out.source_normalized_sha256 = sha256(source)
                out.arrival_threshold_m = threshold_m
                out.duration_method = "left-held saved-frame interval; final frame has zero interval"
                out.area_method = "known flooded area; unknown_area_m2 is reported separately, never treated as dry"
                out.baseline_water = "none defined for this synthetic case"
            tmp.replace(destination)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    return {"product_file": destination.name, "product_sha256": sha256(destination),
            "source_normalized_sha256": sha256(source), "arrival_threshold_m": threshold_m,
            "frames": len(times), "cells": n, "status": "COMPUTED_FROM_SAVED_NUMERICAL_OUTPUT"}


def _select_cells(ds, bbox, limit=MAX_RESPONSE_CELLS):
    xmin, ymin, xmax, ymax = bbox
    if not all(math.isfinite(v) for v in bbox) or xmin >= xmax or ymin >= ymax:
        raise ValueError("Invalid metric bbox")
    found = []
    n = len(ds.dimensions["cell"])
    for start in range(0, n, CELL_BLOCK):
        stop = min(n, start + CELL_BLOCK)
        x = np.asarray(ds["x"][start:stop])
        y = np.asarray(ds["y"][start:stop])
        found.extend(start + int(j) for j in np.flatnonzero((xmin <= x) & (x <= xmax) & (ymin <= y) & (y <= ymax)))
        if len(found) > limit:
            raise ValueError("Window exceeds 2048 cells; request a smaller metric bbox")
    return found


def _field_at(ds, name, frame, cells):
    # Bound each native read to one scalar; selected cells are <=2048.
    result = []
    for cell in cells:
        value = _array(ds[name], (frame, cell))
        number = float(value)
        result.append(number if math.isfinite(number) else None)
    return result


def window(source: Path, bbox, *, first_frame: int, frame_count: int, field: str):
    if field not in {"h", "eta", "u", "v", "wet", "velocity_magnitude"}:
        raise ValueError("Unsupported native result field")
    if frame_count < 1 or frame_count > MAX_RESPONSE_FRAMES or first_frame < 0:
        raise ValueError("Window exceeds bounded frame limit")
    with netCDF4.Dataset(source) as ds:
        if first_frame + frame_count > len(ds.dimensions["time"]):
            raise ValueError("Frame window outside saved result")
        cells = _select_cells(ds, bbox)
        if not cells:
            return {"state": "NO_CELLS_IN_WINDOW", "cells": [], "frames": []}
        geometry = [{"cell": c, "x": float(ds["x"][c]), "y": float(ds["y"][c]),
                     "area_m2": float(ds["cell_area"][c])} for c in cells]
        frames = []
        for i in range(first_frame, first_frame + frame_count):
            valid = _field_at(ds, "valid", i, cells)
            if field == "velocity_magnitude":
                uu = _field_at(ds, "u", i, cells)
                vv = _field_at(ds, "v", i, cells)
                values = [math.hypot(u, v) if u is not None and v is not None else None
                          for u, v in zip(uu, vv)]
            else:
                values = _field_at(ds, field, i, cells)
            states = ["NODATA" if not flag else "DRY" if float(ds["h"][i, c]) < ds.wet_threshold_m else "WET"
                      for c, flag in zip(cells, valid)]
            frames.append({"frame": i, "elapsed_s": float(ds["time"][i]), "values": values, "states": states})
        return {"state": "AVAILABLE", "cells": geometry, "frames": frames, "field": field}


def point_series(source: Path, *, cell: int, first_frame=0, frame_count=None):
    if (frame_count is not None and (frame_count < 1 or frame_count > MAX_RESPONSE_FRAMES)) or first_frame < 0:
        raise ValueError("Time window exceeds 32 frames")
    with netCDF4.Dataset(source) as ds:
        if cell < 0 or cell >= len(ds.dimensions["cell"]):
            return {"state": "OUTSIDE_DOMAIN", "series": []}
        if frame_count is None:
            frame_count = min(MAX_RESPONSE_FRAMES, len(ds.dimensions["time"]) - first_frame)
        if frame_count < 1 or first_frame + frame_count > len(ds.dimensions["time"]):
            raise ValueError("Frame window outside saved result")
        series = []
        for i in range(first_frame, first_frame + frame_count):
            valid = bool(ds["valid"][i, cell])
            h = float(ds["h"][i, cell]) if valid else None
            series.append({"frame": i, "elapsed_s": float(ds["time"][i]),
                           "depth_m": h, "state": "NODATA" if not valid else "DRY" if h < ds.wet_threshold_m else "WET"})
        return {"state": "AVAILABLE", "cell": cell, "x": float(ds["x"][cell]),
                "y": float(ds["y"][cell]), "series": series}


def product_window(source: Path, bbox, field: str):
    if field not in {"maximum_depth_m", "maximum_velocity_m_s", "flood_duration_s", "arrival_elapsed_s", "cell_state"}:
        raise ValueError("Unsupported derived field")
    with netCDF4.Dataset(source) as ds:
        cells = _select_cells(ds, bbox)
        return {"state": "AVAILABLE" if cells else "NO_CELLS_IN_WINDOW", "field": field,
                "cells": [{"cell": c, "x": float(ds["x"][c]), "y": float(ds["y"][c]),
                           "value": None if not np.isfinite(float(_array(ds[field], c))) else float(ds[field][c]),
                           "state": {0: "NODATA", 1: "NOT_REACHED", 2: "REACHED"}[int(ds["cell_state"][c])]}
                          for c in cells]}


def named_location(source: Path, products: Path, *, name: str, x: float, y: float, radius_m: float,
                   first_frame=0, frame_count=None):
    if not name.strip() or len(name) > 120 or not all(math.isfinite(v) for v in (x, y, radius_m)) or radius_m <= 0:
        raise ValueError("Named location requires finite metric coordinates and a positive radius")
    best_cell, best_distance = None, radius_m
    with netCDF4.Dataset(source) as ds:
        for start in range(0, len(ds.dimensions["cell"]), CELL_BLOCK):
            stop = min(start + CELL_BLOCK, len(ds.dimensions["cell"]))
            xx = np.asarray(ds["x"][start:stop], dtype=float)
            yy = np.asarray(ds["y"][start:stop], dtype=float)
            distances = np.hypot(xx - x, yy - y)
            j = int(np.argmin(distances))
            if distances[j] <= best_distance:
                best_cell, best_distance = start + j, float(distances[j])
    if best_cell is None:
        return {"name": name, "state": "OUTSIDE_DOMAIN", "arrival_elapsed_s": None, "series": []}
    series = point_series(source, cell=best_cell, first_frame=first_frame, frame_count=frame_count)
    with netCDF4.Dataset(products) as ds:
        state = {0: "NODATA", 1: "NOT_REACHED", 2: "REACHED"}[int(ds["cell_state"][best_cell])]
        arrival = _array(ds["arrival_elapsed_s"], best_cell)
    return {**series, "name": name, "state": state, "distance_to_cell_m": best_distance,
            "arrival_elapsed_s": float(arrival) if np.isfinite(arrival) else None}
