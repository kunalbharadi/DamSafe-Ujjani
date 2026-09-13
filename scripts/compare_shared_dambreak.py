"""Explicit depth/extent agreement on the verified common 1D-equivalent case."""

import argparse
import hashlib
import json
import platform
from pathlib import Path
from uuid import UUID

import netCDF4
import numpy as np
from damsafe.numerics.diagnostics import compare_series, extent_agreement
from damsafe.numerics.execution import save_json, sha256
from damsafe.numerics.results import validate_result

parser = argparse.ArgumentParser()
parser.add_argument("sph_run")
parser.add_argument("dflow_run")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
ident_sph, ident_dflow = str(UUID(args.sph_run)), str(UUID(args.dflow_run))
directory_sph, directory_dflow = (root / ".local/runs" / ident for ident in (ident_sph, ident_dflow))
manifest_sph = json.loads((directory_sph / "execution.json").read_text(encoding="utf-8"))
manifest_dflow = json.loads((directory_dflow / "execution.json").read_text(encoding="utf-8"))
if manifest_sph["state"] != "SUCCEEDED" or manifest_dflow["state"] != "SUCCEEDED":
    raise ValueError("Both genuine solver runs and normalization must succeed")
if manifest_sph["engine"]["engine"] != "dualsphysics" or manifest_sph["case"]["case_id"] != "CaseDambreakVal2D":
    raise ValueError("SPH run is not the pinned vertical-section dam break")
if manifest_dflow["engine"]["engine"] != "dflowfm" or manifest_dflow["case"]["case_id"] != "closed_tank_column_collapse_1d_equivalent":
    raise ValueError("D-Flow run is not the specified horizontal-channel dam break")
if manifest_sph["case"]["physical_case"] != {
    "domain_m": [0, 4, 0, 3], "initial_column_m": [0, 1, 0, 2],
    "gravity_m_s2": 9.81, "end_time_s": 2, "output_interval_s": 0.01,
    "boundaries": "closed bottom and lateral walls, free surface", "geometry": "2D x/z section",
}:
    raise ValueError("SPH geometry/forcing changed; re-establish comparability")
flow_physical = manifest_dflow["case"]["physical_case"]
if any(flow_physical.get(key) != value for key, value in {
    "horizontal_domain_m": [0, 4, 0, 1], "bed_m": 0,
    "initial_column_x_m": [0, 1], "initial_depth_m": 2,
    "initial_volume_m3_per_m_breadth": 2, "gravity_m_s2": 9.81,
    "closed_boundaries": True, "external_forcing": "none", "end_time_s": 2,
    "output_interval_s": 0.01,
}.items()):
    raise ValueError("D-Flow geometry/forcing changed; re-establish comparability")
common = {
    "horizontal_x_m": [0, 4], "transverse_breadth_m": 1,
    "flat_bed_m": 0, "initial_column_x_m": [0, 1], "initial_depth_m": 2,
    "initial_volume_m3_per_m_breadth": 2, "gravity_m_s2": 9.81,
    "closed_boundaries": True, "forcing": "none", "duration_s": 2,
    "gauges_x_m": [0.525, 1.525, 2.525, 3.525],
}
physical_hash = hashlib.sha256(json.dumps(common, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
validate_result(directory_sph / "normalized.nc")
validate_result(directory_dflow / "normalized.nc")
with netCDF4.Dataset(directory_sph / "normalized.nc") as sph, netCDF4.Dataset(directory_dflow / "normalized.nc") as flow:
    t_sph, t_flow = np.asarray(sph["time"][:]), np.asarray(flow["time"][:])
    if t_flow[0] < t_sph[0] or t_flow[-1] > t_sph[-1] or abs(t_flow[-1] - 2) > 1e-6:
        raise ValueError("Common requested output times exceed a solver result")
    x_sph, x_flow = np.asarray(sph["x"][:]), np.asarray(flow["x"][:])
    columns = np.round(x_flow, 6)
    unique = np.unique(columns)
    if len(unique) != len(x_sph) or not np.allclose(unique, x_sph, atol=1e-6):
        raise ValueError("Horizontal reporting columns do not align")
    area = np.asarray(flow["cell_area"][:])
    depth_flow = np.asarray(flow["h"][:])
    depth_sph_native = np.asarray(sph["h"][:])
    if not np.isfinite(depth_flow).all() or not np.isfinite(depth_sph_native).all():
        raise ValueError("Benchmark depth field has unavailable cells")
    depth_flow_column = np.column_stack([
        np.average(depth_flow[:, columns == x], axis=1, weights=area[columns == x]) for x in unique
    ])
    depth_sph_column = np.column_stack([
        np.interp(t_flow, t_sph, depth_sph_native[:, i]) for i in range(len(x_sph))
    ])
    if not np.allclose([area[columns == x].sum() for x in unique], 0.05, atol=1e-8):
        raise ValueError("D-Flow columns do not have 0.05 m2 unit-breadth area")
    gauges = {}
    for x in common["gauges_x_m"]:
        i = int(np.argmin(np.abs(unique - x)))
        if abs(unique[i] - x) > 1e-6:
            raise ValueError("Requested common gauge is off-grid")
        gauges[str(x)] = compare_series(
            t_flow, depth_sph_column[:, i], t_flow, depth_flow_column[:, i],
            compatible_case_hash_a=physical_hash, compatible_case_hash_b=physical_hash,
        )
    extent = [
        extent_agreement(a >= 0.01, b >= 0.01, np.ones(len(unique), bool), np.full(len(unique), 0.05))
        for a, b in zip(depth_sph_column, depth_flow_column, strict=True)
    ]
    speed_sph = np.asarray(sph["u"][:])
    speed_flow = np.asarray(flow["u"][:])
    wet_flow = depth_flow > 0.1
    wet_sph = depth_sph_native > 0.1
    speed_report = {
        "maximum_absolute_sph_u_m_s_on_h_gt_0p1m": float(np.nanmax(np.abs(speed_sph[wet_sph]))),
        "maximum_absolute_dflow_u_m_s_on_h_gt_0p1m": float(np.nanmax(np.abs(speed_flow[wet_flow]))),
        "interpretation": "SPH volume-weighted column x velocity versus D-Flow depth-averaged face x velocity; no comparison in breaking/impact zones",
    }
report = {
    "kind": "physically matched synthetic 1D-equivalent benchmark agreement",
    "scientific_status": "inter-model agreement, not accuracy or Ujjani validation",
    "physical_case": common,
    "physical_case_sha256": physical_hash,
    "sph": {"run_id": ident_sph, "manifest_sha256": sha256(directory_sph / "execution.json"), "normalized_sha256": sha256(directory_sph / "normalized.nc"), "particle_spacing_m": manifest_sph["case"]["particle_spacing_m"], "stage_runtime_seconds": sum(s["elapsed_seconds"] for s in manifest_sph["stages"])},
    "dflow": {"run_id": ident_dflow, "manifest_sha256": sha256(directory_dflow / "execution.json"), "normalized_sha256": sha256(directory_dflow / "normalized.nc"), "mesh_dx_m": 0.05, "mesh_dy_m": 0.5, "stage_runtime_seconds": sum(s["elapsed_seconds"] for s in manifest_dflow["stages"])},
    "common_times_s": t_flow.tolist(),
    "time_alignment": "SPH native depth linearly interpolated within its saved 0.01 s cadence to D-Flow times; no extrapolation",
    "gauge_depth_agreement_m": gauges,
    "extent_iou": {"mean": float(np.mean([e["iou"] for e in extent if e["iou"] is not None])), "minimum": float(np.min([e["iou"] for e in extent if e["iou"] is not None])), "final": extent[-1]["iou"]},
    "velocity_context": speed_report,
    "hardware": {"host": platform.platform(), "processor": platform.processor(), "container_cpu_limit_each": 2, "container_memory_mb_each": 2048},
    "limits": "SPH weakly compressible 2D x/z includes vertical motion and particle loss; D-Flow shallow-water depth is 2D horizontal. Agreement cannot validate either against truth; spray/impact zones excluded from shallow-water interpretation.",
}
destination = root / f"docs/evidence/phase2/shared-comparison-{ident_sph}-{ident_dflow}.json"
save_json(destination, report)
print(destination)
print({"gauges_rmse_m": {x: r["rmse"] for x, r in gauges.items()}, "final_extent_iou": extent[-1]["iou"]})
