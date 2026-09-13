"""Quantify differences among executed synthetic benchmark resolutions.

These are sensitivity differences between solver runs, not errors against truth.
"""

import json
from pathlib import Path

import netCDF4
import numpy as np
from damsafe.numerics.execution import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".local/runs"
IDS = {
    "dflow_baseline_0p05m_0p01s": "5f337ace-316f-487b-8962-330e97a11685",
    "dflow_coarse_0p10m_0p01s": "4e2a2a76-a878-4c4d-ab20-797e7d3d01db",
    "dflow_short_step_0p05m_0p005s": "31597407-e29e-431e-a83a-64fd56b296c5",
    "dflow_fine_0p025m_0p005s": "12f99e60-72c1-4aee-ba64-4f90f64d548e",
    "sph_official_0p01m": "424a48cf-e381-4599-ac9a-25817559fe09",
    "sph_variant_0p02m": "7eac17d0-15d0-4113-91b1-8f3461329a5c",
}
GAUGES = (0.525, 1.525, 2.525, 3.525)


def read_run(ident, dflow):
    path = RUNS / ident / "normalized.nc"
    with netCDF4.Dataset(path) as ds:
        t = np.asarray(ds["time"][:], dtype=float)
        x = np.asarray(ds["x"][:], dtype=float)
        h = np.asarray(ds["h"][:], dtype=float)
        area = np.asarray(ds["cell_area"][:], dtype=float)
        if dflow:
            columns, inverse = np.unique(np.round(x, 8), return_inverse=True)
            weights = np.bincount(inverse, weights=area)
            h = np.stack([np.bincount(inverse, weights=row * area) / weights for row in h])
            x = columns
        volume = np.asarray(ds["h"][:], dtype=float) @ area
    manifest = RUNS / ident / "execution.json"
    return {
        "id": ident,
        "x": x,
        "time": t,
        "depth": h,
        "volume": volume,
        "normalized_sha256": sha256(path),
        "manifest_sha256": sha256(manifest),
        "runtime_s": sum(
            stage.get("elapsed_seconds", 0)
            for stage in json.loads(manifest.read_text(encoding="utf-8"))["stages"]
        ),
    }


def compare(reference, candidate):
    # The native outputs have the same physical origin; interpolate only within
    # the saved candidate time span and report on the reference's spatial grid.
    common = reference["time"] <= candidate["time"][-1] + 1e-7
    t = reference["time"][common]
    if t[0] < candidate["time"][0] - 1e-7:
        raise ValueError("Candidate starts after reference")
    at_x = np.stack(
        [np.interp(reference["x"], candidate["x"], row) for row in candidate["depth"]]
    )
    at_t = np.stack([np.interp(t, candidate["time"], at_x[:, j]) for j in range(len(reference["x"]))], axis=1)
    delta = reference["depth"][common] - at_t
    gauges = {}
    for gauge in GAUGES:
        j = int(np.argmin(abs(reference["x"] - gauge)))
        gauges[str(gauge)] = {
            "depth_rmse_m": float(np.sqrt(np.mean(delta[:, j] ** 2))),
            "peak_depth_difference_m": float(np.max(reference["depth"][common, j]) - np.max(at_t[:, j])),
            "peak_time_difference_s": float(t[np.argmax(reference["depth"][common, j])] - t[np.argmax(at_t[:, j])]),
        }
    return {
        "reference_run_id": reference["id"],
        "candidate_run_id": candidate["id"],
        "common_frames": len(t),
        "depth_rmse_m": float(np.sqrt(np.mean(delta**2))),
        "maximum_absolute_depth_difference_m": float(np.max(abs(delta))),
        "gauges": gauges,
    }


def public(run):
    return {
        "id": run["id"],
        "columns": len(run["x"]),
        "frames": len(run["time"]),
        "runtime_s": run["runtime_s"],
        "initial_volume_native_units": float(run["volume"][0]),
        "final_volume_native_units": float(run["volume"][-1]),
        "normalized_sha256": run["normalized_sha256"],
        "manifest_sha256": run["manifest_sha256"],
    }


if __name__ == "__main__":
    runs = {name: read_run(ident, name.startswith("dflow")) for name, ident in IDS.items()}
    baseline = runs["dflow_baseline_0p05m_0p01s"]
    sph = runs["sph_official_0p01m"]
    report = {
        "status": "executed synthetic benchmark sensitivity; differences are not accuracy",
        "runs": {name: public(run) for name, run in runs.items()},
        "dflow_vs_baseline": {
            name: compare(baseline, run) for name, run in runs.items() if name.startswith("dflow") and run is not baseline
        },
        "sph_particle_spacing_0p01_vs_0p02m": compare(sph, runs["sph_variant_0p02m"]),
        "caveats": [
            "D-Flow mesh and time step vary; one pair isolates the time step, whereas the fine-grid pair changes both.",
            "SPH output is a 0.05 m reporting-column reduction of native particles; particle mass loss remains unresolved.",
            "Intermodel differences and resolution sensitivity do not establish convergence or Ujjani validation.",
        ],
    }
    target = ROOT / "docs/evidence/phase2/sensitivity.json"
    save_json(target, report)
    print(target)
    for name, result in report["dflow_vs_baseline"].items():
        print(name, result["depth_rmse_m"])
    print("sph", report["sph_particle_spacing_0p01_vs_0p02m"]["depth_rmse_m"])
