"""Physical bookkeeping and model agreement; no accuracy badge from two models."""

import netCDF4
import numpy as np

from .results import finite_array


def native_dflow_balance(history_file, map_file):
    """Audit D-Flow's cumulative global balance against face water volume.

    Component fields are reported separately; some are subdivisions or 1D/2D
    exchange and must not be blindly added to the whole-domain balance.
    """
    names = (
        "total_volume", "storage", "volume_error", "boundaries_in", "boundaries_out",
        "boundaries_total", "exchange_with_1D_total", "precipitation_total",
        "evaporation", "source_sink", "groundwater_total", "laterals_total", "Qext_total",
    )
    with netCDF4.Dataset(history_file) as history, netCDF4.Dataset(map_file) as map_ds:
        if any(f"water_balance_{name}" not in history.variables for name in names):
            raise ValueError("Native D-Flow history lacks required global balance pathways")
        if history["time"].units != map_ds["time"].units:
            raise ValueError("Map and history time origins disagree")
        history_time = finite_array(history["time"][:], "history time", 1)
        map_time = finite_array(map_ds["time"][:], "map time", 1)
        if len(history_time) < 2 or np.any(np.diff(history_time) <= 0):
            raise ValueError("Invalid D-Flow history time")
        if map_time[0] < history_time[0] or map_time[-1] > history_time[-1]:
            raise ValueError("Map times extend beyond water-balance history")
        values = {}
        for name in names:
            var = history[f"water_balance_{name}"]
            if var.dimensions != ("time",) or var.units != "m3":
                raise ValueError(f"Invalid water-balance field {name}")
            raw = np.ma.asarray(var[:])
            if np.any(np.ma.getmaskarray(raw)):
                raise ValueError(f"Masked water-balance field {name}")
            values[name] = finite_array(raw, name, 1)
        for name in ("boundaries_in", "boundaries_out"):
            if np.any(values[name] < 0):
                raise ValueError("Native inflow/outflow pathway has negative cumulative volume")
        map_depth = np.ma.asarray(map_ds["mesh2d_waterdepth"][:])
        map_area = np.ma.asarray(map_ds["mesh2d_flowelem_ba"][:])
        if np.any(np.ma.getmaskarray(map_depth)) or np.any(np.ma.getmaskarray(map_area)):
            raise ValueError("Map face volume unavailable; cannot cross-check native balance")
        if np.any(~np.isfinite(map_depth)) or np.any(map_depth < 0) or np.any(map_area <= 0):
            raise ValueError("Invalid map volume state")
        map_volume = np.sum(map_depth * map_area[None, :], axis=1)
        history_volume_at_map_time = np.interp(map_time, history_time, values["total_volume"])
        map_difference = map_volume - history_volume_at_map_time
        initial = float(values["total_volume"][0])
        storage_difference = values["total_volume"] - initial - values["storage"]
        boundary_difference = values["boundaries_in"] - values["boundaries_out"] - values["boundaries_total"]
        precision = float(10 * np.finfo(np.float32).eps * np.max(values["total_volume"]))
        if max(np.max(np.abs(storage_difference)), np.max(np.abs(boundary_difference)), np.max(np.abs(map_difference))) > precision:
            raise ValueError("Native D-Flow water-balance fields disagree beyond NetCDF reporting precision")
        return {
            "source_history_file": history_file.name,
            "history_frames": len(history_time),
            "time_units": history["time"].units,
            "initial_volume_m3": initial,
            "final_volume_m3": float(values["total_volume"][-1]),
            "pathways_cumulative_final_m3": {name: float(values[name][-1]) for name in names if name not in ("total_volume", "storage", "volume_error")},
            "native_max_absolute_volume_error_m3": float(np.max(np.abs(values["volume_error"]))),
            "map_history_max_absolute_difference_m3": float(np.max(np.abs(map_difference))),
            "reporting_precision_allowance_m3": precision,
            "wet_dry_treatment": "Native global storage and face water depths include the solver's wet/dry state; no extra inferred wetting flux is added.",
            "component_warning": "Qext/laterals subdivisions and 1D/2D exchange are reported, not blindly summed with parent global fields.",
        }


def volume_balance(times, volume, inflow, outflow):
    t = finite_array(times, "time", 1)
    v = finite_array(volume, "volume", 1)
    qi, qo = finite_array(inflow, "inflow", 1), finite_array(outflow, "outflow", 1)
    if not len(t) == len(v) == len(qi) == len(qo) or len(t) < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("Balance arrays must share increasing times")
    if np.any(v < 0) or np.any(qi < 0) or np.any(qo < 0):
        raise ValueError("Volume and separately signed inflow/outflow pathways must be nonnegative")
    delta = np.diff(t)
    net = qi - qo
    cumulative = np.r_[0, np.cumsum(0.5 * (net[1:] + net[:-1]) * delta)]
    residual = v - v[0] - cumulative
    scale = max(float(v[0]), float(np.sum(0.5 * (qi[1:] + qi[:-1]) * delta)))
    return {
        "residual_m3": residual.tolist(),
        "maximum_absolute_residual_m3": float(np.max(np.abs(residual))),
        "relative_to_initial_or_inflow": float(np.max(np.abs(residual)) / scale) if scale else None,
        "integration": "trapezoidal sampled boundary fluxes; output cadence limits balance accuracy",
        "includes_all_boundaries": "caller must supply every pathway including wet/dry losses",
    }


def prescribed_storage_balance(times, initial_storage, inflow, pathways, level_storage):
    """Continuity audit of prescribed pathways, NOT a computed breach-outflow method."""
    t = finite_array(times, "time", 1)
    curve = finite_array(level_storage, "level-storage", 2)
    if (
        curve.shape[1] != 2
        or len(curve) < 2
        or np.any(np.diff(curve, axis=0) <= 0)
        or np.any(curve[:, 1] < 0)
    ):
        raise ValueError("Level and storage pairs must be strictly increasing, storage nonnegative")
    if not np.isfinite(initial_storage) or not curve[0, 1] <= initial_storage <= curve[-1, 1]:
        raise ValueError("Initial storage outside documented curve")
    if len(set(pathways)) != len(pathways) or not pathways:
        raise ValueError("Supply distinct release pathways")
    qi = finite_array(inflow, "inflow", 1)
    parts = [finite_array(q, name, 1) for name, q in pathways.items()]
    if len(t) < 2 or any(len(q) != len(t) for q in [qi, *parts]) or np.any(np.diff(t) <= 0):
        raise ValueError("Fluxes need matching increasing times")
    if any(np.any(q < 0) for q in [qi, *parts]):
        raise ValueError("Pathway discharge cannot be negative")
    qo = np.sum(parts, axis=0)
    net = qi - qo
    storage = initial_storage + np.r_[0, np.cumsum(0.5 * (net[1:] + net[:-1]) * np.diff(t))]
    extrema = list(storage)
    for i, duration in enumerate(np.diff(t)):
        slope = (net[i+1]-net[i])/duration
        if slope:
            offset = -net[i]/slope
            if 0 < offset < duration:
                extrema.append(storage[i]+net[i]*offset+.5*slope*offset**2)
    if min(extrema) < curve[0, 1] or max(extrema) > curve[-1, 1]:
        raise ValueError("Prescribed fluxes exceed available water or documented storage range")
    return {
        "storage_m3": storage.tolist(),
        "level_m": np.interp(storage, curve[:, 1], curve[:, 0]).tolist(),
        "balance": volume_balance(t, storage, qi, qo),
        "method": "prescribed continuity only; no breach prediction",
    }


def compare_series(times_a, values_a, times_b, values_b, *, compatible_case_hash_a, compatible_case_hash_b):
    if not compatible_case_hash_a or compatible_case_hash_a != compatible_case_hash_b:
        raise ValueError("Comparison requires the same documented physical case")
    ta, tb = finite_array(times_a, "time A", 1), finite_array(times_b, "time B", 1)
    a, b = finite_array(values_a, "values A", 1), finite_array(values_b, "values B", 1)
    if (
        len(a) != len(ta)
        or len(b) != len(tb)
        or not np.array_equal(ta, tb)
        or len(ta) < 2
        or np.any(np.diff(ta) <= 0)
    ):
        raise ValueError("Use identical saved output times and compatible gauges; no silent interpolation")
    diff = a - b
    return {
        "kind": "inter-model agreement",
        "bias": float(diff.mean()),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "maximum_absolute_difference": float(np.max(np.abs(diff))),
        "peak_difference": float(a.max() - b.max()),
        "peak_time_difference_seconds": float(ta[a.argmax()] - tb[b.argmax()]),
    }


def extent_agreement(a, b, valid, cell_area):
    a, b, valid = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool), np.asarray(valid, dtype=bool)
    area = finite_array(cell_area, "area")
    if not a.shape == b.shape == valid.shape == area.shape or np.any(area <= 0):
        raise ValueError("Extent masks need a common grid and positive metric areas")
    union = float(area[(a | b) & valid].sum())
    intersection = float(area[a & b & valid].sum())
    return {
        "kind": "inter-model extent agreement",
        "intersection_m2": intersection,
        "union_m2": union,
        "iou": intersection / union if union else None,
        "empty_union": union == 0,
        "valid_area_m2": float(area[valid].sum()),
    }
