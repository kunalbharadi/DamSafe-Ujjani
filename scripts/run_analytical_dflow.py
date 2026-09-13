"""Run a still-water analytical check from the pinned D-Flow example mesh."""

import re
from pathlib import Path
from uuid import uuid4

import netCDF4
import numpy as np
from damsafe.numerics.adapters import capabilities, prepare_official, run_stages
from damsafe.numerics.execution import Limits, save_json, sha256
from damsafe.numerics.worker import finalize

root = Path(__file__).resolve().parents[1]
ident = str(uuid4())
directory = root / ".local/runs" / ident
capability = capabilities("dflowfm")
if not capability["available"]:
    print(capability)
    raise SystemExit(2)
case = prepare_official("dflowfm", directory)
model = directory / "dflowfm"
paths = {name: model / name for name in ("f34_net.nc", "f34.mdu", "f34_001.bc", "f34_bnd.ext")}
source_hashes = {name: sha256(path) for name, path in paths.items()}

# Uniform zero bed makes the exact rest state eta=h=1.9 m on every face.
with netCDF4.Dataset(paths["f34_net.nc"], "a") as grid:
    if grid["NetNode_z"].units != "m":
        raise ValueError("Unexpected source mesh bed units")
    grid["NetNode_z"][:] = 0.0

boundary = paths["f34_001.bc"].read_text(encoding="utf-8")
boundary, nmean = re.subn(r"(?m)^0\s+0\s+0\s*$", "0 1.9 0", boundary)
boundary, ntide = re.subn(r"(?m)^750\s+1\.5\s+[-\d.]+\s*$", "750 0 0", boundary)
if (nmean, ntide) != (3, 3):
    raise ValueError("Official forcing pattern changed; analytical case was not prepared")
paths["f34_001.bc"].write_text(boundary, encoding="utf-8")

external = paths["f34_bnd.ext"].read_text(encoding="utf-8")
if external.count("[Spatial]") != 1:
    raise ValueError("Unexpected wind forcing layout")
paths["f34_bnd.ext"].write_text(external.split("[Spatial]")[0], encoding="utf-8")

mdu = paths["f34.mdu"].read_text(encoding="utf-8")
for key in ("ThinDamFile", "DryPointsFile"):
    mdu, count = re.subn(rf"(?m)^({key}\s*=).*?$", r"\1 ", mdu)
    if count != 1:
        raise ValueError(f"Expected one {key} in pinned example")
paths["f34.mdu"].write_text(mdu, encoding="utf-8")

case.update(
    case_kind="ANALYTICAL_BENCHMARK",
    case_id="f34_uniform_lake_at_rest",
    source_case="01_dflowfm_sequential",
    source_input_sha256=source_hashes,
    input_sha256={name: sha256(path) for name, path in paths.items()},
    physical_case={
        "reference": "hydrostatic shallow-water rest state",
        "uniform_bed_m": 0.0,
        "initial_and_boundary_eta_m": 1.9,
        "expected_u_v_m_s": 0.0,
        "forcing": "constant 1.9 m boundary; no wind/tide/rain; thin dams and forced dry points removed",
        "time_origin": "1990-08-05T00:00:00+00:00",
        "end_time_s": 90000,
    },
)
save_json(directory / "input-manifest.json", case)
print(f"Run {ident}: {directory}", flush=True)
result = run_stages("dflowfm", directory, ident, capability, Limits(timeout_seconds=1200, output_bytes=2_000_000_000))
if result["state"] == "SUCCEEDED":
    try:
        result["normalization"] = finalize("dflowfm", directory, case, capability)
        with netCDF4.Dataset(directory / "normalized.nc") as output:
            wet = np.asarray(output["wet"][:] == 1)
            if not wet.any():
                raise ValueError("Analytical benchmark contains no wet cells")
            values = {name: np.ma.asarray(output[name][:]).filled(np.nan) for name in ("h", "eta", "u", "v")}
            if any(not np.isfinite(value[wet]).all() for value in values.values()):
                raise ValueError("Analytical benchmark lacks finite wet-cell observables")
            result["analytical_reference"] = {
                "kind": "exact uniform lake-at-rest shallow-water state",
                "reference_eta_m": 1.9,
                "reference_h_m": 1.9,
                "reference_u_v_m_s": 0.0,
                "max_absolute_eta_error_m": float(np.max(np.abs(values["eta"][wet] - 1.9))),
                "max_absolute_h_error_m": float(np.max(np.abs(values["h"][wet] - 1.9))),
                "max_absolute_speed_m_s": float(np.max(np.hypot(values["u"][wet], values["v"][wet]))),
                "wet_face_frames": int(wet.sum()),
                "analytic_basis": "zero slope/velocity and equal constant initial/open-boundary surface is an exact rest solution of 2D shallow-water equations",
            }
    except Exception as exc:  # noqa: BLE001 -- preserve native success but fail assessment
        result = {**result, "state": "FAILED", "assessment_error": str(exc)}
manifest = {"id": ident, "engine": capability, "case": case, "execution_origin": "LOCAL", "evidence_status": "UNASSESSED", **result}
save_json(directory / "execution.json", manifest)
save_json(root / f"docs/evidence/phase2/dflowfm-lake-{ident}.json", manifest)
print(result["state"], flush=True)
raise SystemExit(0 if result["state"] == "SUCCEEDED" else 1)
