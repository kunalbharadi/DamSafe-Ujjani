"""Run a physically specified 1D-equivalent dam break in D-Flow FM.

The channel is 4 m long and 1 m wide. A 2 m column initially occupies x<1 m.
This is comparable per unit breadth to DualSPHysics CaseDambreakVal2D, but
impact/splash regions violate shallow-water assumptions.
"""

import argparse
import re
from pathlib import Path
from uuid import uuid4

import netCDF4
import numpy as np
from damsafe.numerics.adapters import capabilities, prepare_official, run_stages
from damsafe.numerics.execution import Limits, save_json, sha256
from damsafe.numerics.worker import finalize


def rectangular_net(path: Path, nx=80, ny=2):
    """Write the pinned example's legacy NetNode/NetLink UGRID schema."""
    nodes = np.asarray([(4 * i / nx, j / ny) for j in range(ny + 1) for i in range(nx + 1)])

    def index(i, j):
        return 1 + j * (nx + 1) + i

    links, boundary = [], []
    for j in range(ny + 1):
        for i in range(nx):
            links.append((index(i, j), index(i + 1, j)))
            if j in (0, ny):
                boundary.append(len(links))
    for j in range(ny):
        for i in range(nx + 1):
            links.append((index(i, j), index(i, j + 1)))
            if i in (0, nx):
                boundary.append(len(links))
    faces = np.asarray(
        [
            (index(i, j), index(i + 1, j), index(i + 1, j + 1), index(i, j + 1))
            for j in range(ny) for i in range(nx)
        ], dtype="i4",
    )
    with netCDF4.Dataset(path, "w", format="NETCDF3_CLASSIC") as grid:
        for name, length in (
            ("nNetNode", len(nodes)), ("nNetLink", len(links)), ("nNetLinkPts", 2),
            ("nBndLink", len(boundary)), ("nNetElem", len(faces)), ("nNetElemMaxNode", 4),
        ):
            grid.createDimension(name, length)
        grid.Conventions = "CF-1.5:Deltares-0.1"
        grid.source = "DamSafe synthetic rectangular benchmark based on pinned D-Flow NetNode schema"
        for name, data in (("NetNode_x", nodes[:, 0]), ("NetNode_y", nodes[:, 1]), ("NetNode_z", np.zeros(len(nodes)))):
            variable = grid.createVariable(name, "f8", ("nNetNode",))
            variable[:] = np.asarray(data)
            variable.units = "m"
            variable.grid_mapping = "projected_coordinate_system"
        grid["NetNode_z"].positive = "up"
        projection = grid.createVariable("projected_coordinate_system", "i4")
        projection.assignValue(0)
        projection.setncattr("name", "local Cartesian benchmark")
        projection.grid_mapping_name = "Unknown projected"
        projection.epsg = 0
        projection.EPSG_code = "LOCAL"
        for name, data, dimensions in (
            ("NetLink", links, ("nNetLink", "nNetLinkPts")),
            ("NetLinkType", np.full(len(links), 2), ("nNetLink",)),
            ("NetElemNode", faces, ("nNetElem", "nNetElemMaxNode")),
            ("BndLink", boundary, ("nBndLink",)),
        ):
            variable = grid.createVariable(name, "i4", dimensions)
            variable[:] = data


def set_mdu(text, key, value):
    changed, count = re.subn(rf"(?m)^({re.escape(key)}\s*=).*?$", rf"\g<1> {value}", text)
    if count != 1:
        raise ValueError(f"Expected exactly one pinned MDU setting {key}")
    return changed


parser = argparse.ArgumentParser()
parser.add_argument("--nx", type=int, choices=(40, 80, 160), default=80)
parser.add_argument("--dt-max", type=float, choices=(0.005, 0.01), default=0.01)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
ident = str(uuid4())
directory = root / ".local/runs" / ident
capability = capabilities("dflowfm")
if not capability["available"]:
    print(capability)
    raise SystemExit(2)
case = prepare_official("dflowfm", directory)
model = directory / "dflowfm"
rectangular_net(model / "dam_net.nc", nx=args.nx)
mdu = (model / "f34.mdu").read_text(encoding="utf-8")
for key, value in (
    ("NetFile", "dam_net.nc"), ("WaterLevIni", "0"),
    ("ThinDamFile", ""), ("DryPointsFile", ""), ("ExtForceFileNew", ""),
    ("ObsFile", ""), ("CrsFile", ""), ("Tunit", "S"),
    ("StartDateTime", "19900805000000"), ("StopDateTime", "19900805000002"),
    ("DtUser", "0.01"), ("DtMax", str(args.dt_max)), ("MapInterval", "0.01"), ("HisInterval", "0.01"),
    ("UnifFrictCoef", "0"), ("Vicouv", "0"), ("Turbulencemodel", "0"),
    ("Epshu", "0.01"), ("Limtyphu", "1"), ("CFLMax", "0.4"),
):
    mdu = set_mdu(mdu, key, value)
mdu, inserted = re.subn(r"(?m)^(WaterLevIniFile\s*=.*)$", r"\1\nIniFieldFile = dam_init.ext", mdu)
if inserted != 1:
    raise ValueError("Pinned MDU geometry section changed")
mdu, inserted = re.subn(r"(?m)^\[numerics\]$", "[numerics]\nMinTimestepBreak = 0.000001", mdu)
if inserted != 1:
    raise ValueError("Pinned MDU numerics section changed")
(model / "f34.mdu").write_text(mdu, encoding="utf-8")

# The pinned engine source tests this exact [Spatial] sample/triangulation
# mechanism for initialWaterLevel. Duplicate samples near x=1 locate the step
# between cell centres without prescribing a perpetual discharge boundary.
(model / "dam_init.ext").write_text(
    "[General]\nfileVersion = 3.00\nfileType = extForce\n\n[Spatial]\n"
    "quantity = initialwaterlevel\nforcingFile = dam_init.xyz\n"
    "forcingFileType = sample\ninterpolationMethod = triangulation\n",
    encoding="utf-8",
)
with (model / "dam_init.xyz").open("w", encoding="utf-8") as file:
    for y in (-0.1, 0.0, 0.5, 1.0, 1.1):
        for x in (-0.1, 0.0, 0.9, 0.999, 1.001, 1.1, 4.0, 4.1):
            file.write(f"{x} {y} {2.0 if x < 1 else 0.0}\n")
files = ("dam_net.nc", "f34.mdu", "dam_init.ext", "dam_init.xyz", "f34_001.bc", "f34_bnd.ext")
case.update(
    case_kind="SHARED_SYNTHETIC_BENCHMARK",
    case_id="closed_tank_column_collapse_1d_equivalent",
    source_case="01_dflowfm_sequential",
    input_sha256={name: sha256(model / name) for name in files},
    physical_case={
        "horizontal_domain_m": [0, 4, 0, 1], "bed_m": 0,
        "initial_column_x_m": [0, 1], "initial_depth_m": 2,
        "initial_volume_m3_per_m_breadth": 2,
        "gravity_m_s2": 9.81, "closed_boundaries": True,
        "external_forcing": "none", "end_time_s": 2,
        "output_interval_s": 0.01,
        "mesh_dx_m": 4 / args.nx,
        "mesh_dy_m": 0.5,
        "maximum_time_step_s": args.dt_max,
        "comparison_interpretation": "D-Flow horizontal 2D channel depth averaged over unit breadth versus DualSPHysics vertical x/z section per unit breadth",
    },
)
save_json(directory / "input-manifest.json", case)
print(f"Run {ident}: {directory}", flush=True)
result = run_stages("dflowfm", directory, ident, capability, Limits(timeout_seconds=1200, output_bytes=2_000_000_000))
if result["state"] == "SUCCEEDED":
    try:
        result["normalization"] = finalize("dflowfm", directory, case, capability)
        with netCDF4.Dataset(directory / "normalized.nc") as output:
            x = np.asarray(output["x"][:])
            y = np.asarray(output["y"][:])
            h0 = np.asarray(output["h"][0])
            area = np.asarray(output["cell_area"][:])
            if np.min(x) < 0 or np.max(x) > 4 or np.min(y) < 0 or np.max(y) > 1:
                raise ValueError("Generated geometry escaped the shared physical domain")
            initial_volume = float(np.sum(h0 * area))
            if abs(initial_volume - 2) > 0.02:
                raise ValueError(f"Initial volume {initial_volume} m3 differs from the specified 2 m3")
            result["physical_checks"] = {"initial_volume_m3": initial_volume, "closed_domain": True}
    except Exception as exc:  # noqa: BLE001 -- preserve failed generated-model evidence
        result = {**result, "state": "FAILED", "assessment_error": str(exc)}
manifest = {"id": ident, "engine": capability, "case": case, "execution_origin": "LOCAL", "evidence_status": "UNASSESSED", **result}
save_json(directory / "execution.json", manifest)
save_json(root / f"docs/evidence/phase2/dflowfm-shared-{ident}.json", manifest)
print(result["state"], flush=True)
raise SystemExit(0 if result["state"] == "SUCCEEDED" else 1)
