"""Normalize authentic DualSPHysics 2D particles with explicit averaging assumptions."""

import csv
import re
from pathlib import Path

import numpy as np

from .execution import sha256
from .results import create_result, finite_array, validate_result, write_frame


def read_partvtk(path: Path):
    """Read the bounded binary legacy POLYDATA layout emitted by PartVTK.

    VTK legacy binary values are big endian. Unknown layouts fail closed so a
    partial or mis-staggered particle frame cannot become a numerical result.
    """
    data = path.read_bytes()
    if len(data) > 100_000_000:
        raise ValueError("Oversized native particle frame")
    position = 0

    def line():
        nonlocal position
        end = data.find(b"\n", position)
        if end < 0:
            raise ValueError("Truncated VTK header")
        value = data[position:end].rstrip(b"\r").decode("ascii")
        position = end + 1
        return value

    def array(count, dtype):
        nonlocal position
        kind = {"float": ">f4", "double": ">f8", "unsigned_int": ">u4", "int": ">i4", "unsigned_char": "u1"}.get(dtype)
        if kind is None:
            raise ValueError(f"Unsupported VTK scalar type {dtype}")
        size = np.dtype(kind).itemsize * count
        end = position + size
        if end > len(data):
            raise ValueError("Truncated VTK binary array")
        result = np.frombuffer(data, dtype=kind, count=count, offset=position).copy()
        position = end
        if data[position:position + 1] not in (b"\n", b"\r"):
            raise ValueError("Missing VTK array separator")
        if data[position:position + 2] == b"\r\n":
            position += 2
        else:
            position += 1
        return result

    if not line().startswith("# vtk DataFile Version "):
        raise ValueError("Not a legacy VTK file")
    line()  # title
    if line() != "BINARY" or line() != "DATASET POLYDATA":
        raise ValueError("Expected binary POLYDATA from PartVTK")
    header = line().split()
    if len(header) != 3 or header[0] != "POINTS":
        raise ValueError("VTK POINTS header missing")
    count = int(header[1])
    if not 0 < count <= 1_000_000:
        raise ValueError("Invalid particle count")
    points = array(3 * count, header[2]).reshape(count, 3)
    header = line().split()
    if len(header) != 3 or header[0] != "VERTICES" or int(header[1]) != count or int(header[2]) != 2 * count:
        raise ValueError("Unexpected VTK vertex topology")
    topology = array(2 * count, "int").reshape(count, 2)
    if not np.all(topology[:, 0] == 1) or not np.array_equal(topology[:, 1], np.arange(count)):
        raise ValueError("VTK particle vertex indices disagree")
    if line() != f"POINT_DATA {count}" or line() != "SCALARS Idp unsigned_int" or line() != "LOOKUP_TABLE default":
        raise ValueError("Unexpected VTK point-data layout")
    array(count, "unsigned_int")
    header = line().split()
    if len(header) != 3 or header[:2] != ["FIELD", "FieldData"]:
        raise ValueError("VTK field data missing")
    fields = {}
    for _ in range(int(header[2])):
        spec = line().split()
        if len(spec) != 4 or int(spec[2]) != count:
            raise ValueError("VTK field shape disagrees with particle count")
        name, components, _, dtype = spec
        if name in fields or not 1 <= int(components) <= 4:
            raise ValueError("Duplicate or oversized VTK field")
        fields[name] = array(count * int(components), dtype).reshape(count, int(components))
    if data[position:].strip():
        raise ValueError("Unexpected trailing VTK payload")
    if "Rhop" not in fields or "Vel" not in fields or fields["Rhop"].shape != (count, 1) or fields["Vel"].shape != (count, 3):
        raise ValueError("Native particle density or velocity unavailable")
    return points, fields["Rhop"][:, 0], fields["Vel"]


def normalize_sph(run_dir: Path, destination: Path, case: dict, engine: dict, bin_width=0.05):
    if case["case_id"] != "CaseDambreakVal2D":
        raise ValueError("Only the verified official x/z benchmark convention is supported")
    if not 0 < bin_width <= 0.5 or not np.isclose(4 / bin_width, round(4 / bin_width)):
        raise ValueError("Bins must exactly divide the four-metre benchmark domain")
    output = run_dir / "output"
    log = (output / "Run.out").read_text(encoding="utf-8", errors="replace")
    massmatch = re.search(r"^MassFluid=([0-9.eE+-]+)", log, re.MULTILINE)
    if not massmatch:
        raise ValueError("Native particle mass missing; no inferred mass is allowed")
    mass = float(massmatch.group(1))
    if not np.isfinite(mass) or mass <= 0:
        raise ValueError("Invalid native particle mass")
    with (output / "RunPARTs.csv").open(encoding="utf-8-sig") as file:
        parts = list(csv.DictReader((line for line in file if line.strip() and not line.startswith("#")), delimiter=";"))
    times = np.asarray([float(p["TimeStep [s]"]) for p in parts])
    if not len(times) or times[-1] < case["physical_case"]["end_time_s"] - 1e-6:
        raise ValueError("Truncated solver run: final time not reached")
    files = {
        int(re.search(r"(\d+)\.vtk$", p.name).group(1)): p
        for p in (output / "particles").glob("PartFluid*.vtk")
    }
    if len(files) != len(parts):
        raise ValueError("Particle frames and native output timetable disagree")
    n = round(4 / bin_width)
    x = (np.arange(n) + 0.5) * bin_width
    provenance = {
        "engine": engine,
        "case": case,
        "native_particle_mass_per_m": mass,
        "execution_origin": "LOCAL",
        "input_mode": "SYNTHETIC",
        "evidence_status": "UNASSESSED",
        "crs": "LOCAL_CARTESIAN_2D_UNIT_BREADTH",
        "vertical_reference": "official tank bottom z=0",
        "depth_definition": "volume-equivalent column depth, sum(mass/rho)/bin_width in 2D",
        "eta_definition": "highest particle centre plus half spacing; spray may bias free-surface estimate",
        "velocity_definition": "particle-volume weighted Cartesian x/y velocity in each column",
        "limitations": "2D x/z section, per unit transverse breadth. Not a Ujjani raster; breaking/splash zones not shallow-water-equivalent.",
        "source_log_sha256": sha256(output / "Run.out"),
        "unavailable_fields": [],
    }
    particle_counts, mass_totals, volume_totals = [], [], []
    wall_tolerance_count = 0
    maximum_wall_overshoot = 0.0
    with create_result(
        destination, times, x, np.zeros(n), np.full(n, bin_width), np.zeros(n), provenance, 0.01
    ) as out:
        for i, p in enumerate(parts):
            native = files.get(int(p["Part"]))
            if not native or native.stat().st_size > 100_000_000:
                raise ValueError("Missing/oversized particle frame")
            native_points, native_density, native_velocity = read_partvtk(native)
            points = finite_array(native_points, "particle coordinates", 2)
            density = finite_array(native_density, "particle density", 1)
            velocity = finite_array(native_velocity, "particle velocity", 2)
            if len(points) != len(density) or velocity.shape != points.shape or np.any(density <= 0):
                raise ValueError("Particle variable shapes/densities disagree")
            if np.any(np.abs(points[:, 1]) > 1e-6):
                raise ValueError("Unexpected transverse coordinates for a 2D benchmark")
            if len(points) != int(p["NpfSim"].replace(",", "")):
                raise ValueError("Fluid-only VTK count differs from native fluid count")
            wall_overshoot = np.maximum(-points[:, 0], points[:, 0] - 4)
            if np.any(wall_overshoot > case["particle_spacing_m"] / 2):
                raise ValueError(
                    "Particles farther than half spacing outside the closed tank; account for losses explicitly"
                )
            wall_tolerance_count += int(np.count_nonzero(wall_overshoot > 0))
            maximum_wall_overshoot = max(maximum_wall_overshoot, float(np.max(wall_overshoot)))
            bins = np.clip((points[:, 0] / bin_width).astype(int), 0, n - 1)
            volume = mass / density
            perbin = np.bincount(bins, weights=volume, minlength=n)
            depth = perbin / bin_width
            ux = np.full(n, np.nan)
            uy = np.full(n, np.nan)
            surface = np.full(n, -np.inf)
            active = perbin > 0
            ux[active] = (
                np.bincount(bins, weights=volume * velocity[:, 0], minlength=n)[active] / perbin[active]
            )
            uy[active] = (
                np.bincount(bins, weights=volume * velocity[:, 1], minlength=n)[active] / perbin[active]
            )
            np.maximum.at(surface, bins, points[:, 2] + case["particle_spacing_m"] / 2)
            surface[~active] = np.nan
            write_frame(out, i, depth, surface, ux, uy)
            particle_counts.append(len(points))
            mass_totals.append(mass * len(points))
            volume_totals.append(float(volume.sum()))
    assessment = validate_result(destination)
    initial = mass_totals[0]
    assessment["diagnostics"] = {
        "fluid_particles": particle_counts,
        "mass_kg_per_m": mass_totals,
        "volume_m3_per_m_breadth": volume_totals,
        "maximum_mass_change_kg_per_m": float(np.max(np.abs(np.asarray(mass_totals) - initial))),
        "maximum_relative_volume_change": float(
            np.max(np.abs(np.asarray(volume_totals) - volume_totals[0])) / volume_totals[0]
        ),
        "interpretation": "Closed tank; particle mass is conserved only while no fluid is excluded. Density-based volume may change in weakly compressible SPH.",
        "output_time_resolution_seconds": float(np.max(np.diff(times))),
        "bin_width_m": bin_width,
        "wall_tolerance_particle_samples": wall_tolerance_count,
        "maximum_wall_overshoot_m": maximum_wall_overshoot,
        "wall_assignment_rule": "centres within half one particle spacing of a closed wall are assigned to its edge bin; larger excursions fail normalization",
    }
    return assessment


def assess_front_reference(run_dir: Path, reference: Path):
    """Compare the reference distributed alongside this exact official example."""
    raw = reference.read_text(encoding="cp1252").splitlines()
    ref = np.loadtxt(raw[2:])
    with (run_dir / "output/GaugesSWL_Swl_z003.csv").open(encoding="utf-8-sig") as file:
        rows = list(csv.DictReader((line for line in file if line.strip() and not line.startswith("#")), delimiter=";"))
    times = np.asarray([float(r["time [s]"]) for r in rows])
    x = np.asarray([float(r["swlx [m]"]) for r in rows])
    # Reference points beyond the closed tank cannot be compared to this domain.
    mask = (ref[:, 1] < 4) & (ref[:, 0] >= times[0]) & (ref[:, 0] <= times[-1])
    sampled = np.interp(ref[mask, 0], times, x)
    error = sampled - ref[mask, 1]
    if not len(error):
        raise ValueError("No overlapping benchmark observations")
    return {
        "kind": "agreement with bundled laboratory reference; not Ujjani accuracy",
        "reference_sha256": sha256(reference),
        "reference_citation": raw[0],
        "samples": int(mask.sum()),
        "excluded_outside_tank_or_time": int((~mask).sum()),
        "rmse_m": float(np.sqrt(np.mean(error**2))),
        "bias_m": float(error.mean()),
        "maximum_absolute_error_m": float(np.max(np.abs(error))),
        "reference_times_s": ref[mask, 0].tolist(),
        "reference_front_m": ref[mask, 1].tolist(),
        "simulated_front_m": sampled.tolist(),
        "time_alignment": "linear interpolation of native gauge samples only; no extrapolation",
        "caveat": "Uses the reference coordinate/time convention bundled by the engine authors. Original experiment scaling and gauge-at-z=0.03 versus true front require expert review; no validation badge assigned.",
    }
