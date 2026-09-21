"""Bounded numerical result I/O. Missing fields stay unavailable."""

import json
from pathlib import Path

import netCDF4
import numpy as np


def finite_array(value, name, ndim=None):
    a = np.asarray(value, dtype=float)
    if ndim is not None and a.ndim != ndim:
        raise ValueError(f"{name}: expected {ndim} dimensions")
    if not np.isfinite(a).all():
        raise ValueError(f"{name}: nonfinite values")
    return a


def create_result(path, times, x, y, areas, bed, provenance, threshold):
    times = finite_array(times, "time", 1)
    if len(times) < 2 or np.any(np.diff(times) <= 0):
        raise ValueError("Need >=2 strictly increasing output times")
    n = len(x)
    for value, name in ((x, "x"), (y, "y"), (areas, "area"), (bed, "bed")):
        if finite_array(value, name, 1).size != n:
            raise ValueError("Cell geometry lengths disagree")
    if np.any(np.asarray(areas) <= 0) or not 0 < threshold:
        raise ValueError("Cell areas and wet threshold must be positive")
    out = netCDF4.Dataset(path, "w", format="NETCDF4")
    out.createDimension("time", len(times))
    out.createDimension("cell", n)
    for name, values, dims, units in [
        ("time", times, ("time",), "s"),
        ("x", x, ("cell",), "m"),
        ("y", y, ("cell",), "m"),
        ("cell_area", areas, ("cell",), "m2"),
        ("bed", bed, ("cell",), "m"),
    ]:
        var = out.createVariable(name, "f8", dims)
        var[:] = values
        var.units = units
    for name, unit in [("h", "m"), ("eta", "m"), ("u", "m/s"), ("v", "m/s")]:
        var = out.createVariable(
            name, "f8", ("time", "cell"), zlib=True, fill_value=np.nan, chunksizes=(1, min(n, 4096))
        )
        var.units = unit
    out.createVariable("valid", "i1", ("time", "cell"), zlib=True)
    out.createVariable("wet", "i1", ("time", "cell"), zlib=True, fill_value=-1)
    out.provenance_json = json.dumps(provenance, allow_nan=False)
    out.wet_threshold_m = threshold
    out.schema_version = 1
    return out


def write_frame(out, index, h, eta=None, u=None, v=None):
    depth = np.ma.asarray(h, dtype=float)
    valid = ~np.ma.getmaskarray(depth) & np.isfinite(depth.filled(np.nan))
    if np.any(depth.filled(0)[valid] < 0):
        raise ValueError("Negative water depth in numerical output")
    h_arr = np.where(valid, depth.filled(np.nan), np.nan)
    out["h"][index, :] = h_arr
    out["valid"][index, :] = valid.astype("i1")
    out["wet"][index, :] = np.where(valid, (depth.filled(0) >= out.wet_threshold_m).astype("i1"), -1)
    for name, field in (("eta", eta), ("u", u), ("v", v)):
        if field is not None:
            value = np.ma.asarray(field, dtype=float).filled(np.nan)
            if value.shape != depth.shape:
                raise ValueError(f"{name} staggering/shape differs from cell depth")
            if name == "eta":
                wet_mask = valid & (depth.filled(0) >= out.wet_threshold_m)
                missing_eta = wet_mask & ~np.isfinite(value)
                if np.any(missing_eta):
                    value = np.where(missing_eta, out["bed"][:] + depth.filled(0), value)
            if np.any(~np.isfinite(value[valid & (depth.filled(0) >= out.wet_threshold_m)])):
                raise ValueError(f"{name} nonfinite on wet valid depth cells")
            out[name][index, :] = np.where(valid, value, np.nan)


def normalize_dflow(
    native: Path,
    destination: Path,
    *,
    crs: str,
    datum: str,
    threshold: float,
    source_provenance: dict,
    max_cells=2_000_000,
):
    """2D face-centered Cartesian map files only; no implicit node/edge rotation."""
    mapping = {"h": "mesh2d_waterdepth", "eta": "mesh2d_s1", "u": "mesh2d_ucx", "v": "mesh2d_ucy"}
    with netCDF4.Dataset(native) as src:
        required = [
            "time",
            "mesh2d_face_x",
            "mesh2d_face_y",
            "mesh2d_flowelem_ba",
            "mesh2d_flowelem_bl",
            mapping["h"],
        ]
        if any(n not in src.variables for n in required):
            raise ValueError("D-Flow map missing required time, face geometry, bed/area or depth fields")
        h = src[mapping["h"]]
        if h.ndim != 2 or h.dimensions[0] != "time" or h.shape[1] > max_cells:
            raise ValueError("Only bounded 2D time/face depth is supported")
        n = h.shape[1]
        cell_dim = h.dimensions[1]
        if "face" not in cell_dim.lower():
            raise ValueError("Depth must use explicit face staggering")
        for field, units in [(mapping["h"], "m"), ("mesh2d_face_x", "m"), ("mesh2d_face_y", "m")]:
            if getattr(src[field], "units", None) != units:
                raise ValueError(f"{field}: unknown/unsupported units; no implicit conversion")
        for name in mapping.values():
            if name in src.variables and src[name].dimensions != h.dimensions:
                raise ValueError(f"{name}: incompatible face/node staggering")
        t = src["time"]
        if not getattr(t, "units", "").startswith("seconds since "):
            raise ValueError("D-Flow time must explicitly use seconds since an origin")
        times = finite_array(t[:], "time", 1)
        provenance = {
            **source_provenance,
            "crs": crs,
            "vertical_reference": datum,
            "source_time_units": t.units,
            "source_initial_time": float(times[0]),
            "velocity_orientation": "Cartesian face x/y; geographic and edge-normal velocities unsupported",
            "unavailable_fields": [k for k, v in mapping.items() if v not in src.variables],
            "native_file": native.name,
            "native_topology": "preserved in original NetCDF",
        }
        with create_result(
            destination,
            times - times[0],
            src["mesh2d_face_x"][:],
            src["mesh2d_face_y"][:],
            src["mesh2d_flowelem_ba"][:],
            src["mesh2d_flowelem_bl"][:],
            provenance,
            threshold,
        ) as out:
            for i in range(len(times)):
                frame = {k: src[v][i, :n] if v in src.variables else None for k, v in mapping.items()}
                write_frame(out, i, **frame)
    return validate_result(destination)


def validate_result(path):
    with netCDF4.Dataset(path) as ds:
        if getattr(ds, "schema_version", None) != 1:
            raise ValueError("Unsupported numerical result schema")
        times = finite_array(ds["time"][:], "time", 1)
        if len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError("Corrupted or non-increasing result times")
        valid_count = 0
        for i in range(len(times)):
            h = np.ma.asarray(ds["h"][i]).filled(np.nan)
            valid = np.asarray(ds["valid"][i], dtype=bool)
            wet = np.ma.asarray(ds["wet"][i]).filled(-1)
            if np.any(~np.isfinite(h[valid])) or np.any(h[valid] < 0):
                raise ValueError("Corrupted/nonfinite/negative result state")
            expected = np.where(valid, (h >= ds.wet_threshold_m).astype(int), -1)
            if not np.array_equal(wet, expected):
                raise ValueError("Wet/dry/no-data mask disagreement")
            valid_count += int(valid.sum())
        if not valid_count:
            raise ValueError("Result contains no valid numerical cells")
        return {
            "frames": len(times),
            "cells": len(ds.dimensions["cell"]),
            "duration_seconds": float(times[-1] - times[0]),
            "valid_cell_frames": valid_count,
            "provenance": json.loads(ds.provenance_json),
        }
