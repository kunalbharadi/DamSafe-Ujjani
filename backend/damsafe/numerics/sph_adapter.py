"""SPH Result Normalization Adapter.

Converts actual DualSPHysics binary VTK particle outputs into normalized,
frontend-friendly frame structures for interactive 3D WebGL visualization.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from damsafe.numerics.sph import read_partvtk


def find_sph_run_dir(run_id: str, run_root_override: Path | None = None) -> Path | None:
    """Locate the run directory for a given run ID containing SPH output."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", run_id):
        return None
    candidates = []
    if run_root_override:
        candidates.append(run_root_override / run_id)
        candidates.append(run_root_override)
    candidates.extend([
        Path(".local/runs") / run_id,
        Path("runs") / run_id,
        Path(__file__).resolve().parents[3] / ".local/runs" / run_id,
    ])
    for cand in candidates:
        if cand.exists() and (cand / "output").exists():
            return cand
    return None


def list_available_sph_runs(run_root: Path | None = None) -> list[str]:
    """Find all run IDs that have valid DualSPHysics particle outputs."""
    roots = []
    if run_root:
        roots.append(run_root)
    roots.extend([
        Path(".local/runs"),
        Path("runs"),
        Path(__file__).resolve().parents[3] / ".local/runs",
    ])
    sph_runs = []
    for r in roots:
        if not r.exists():
            continue
        for child in r.iterdir():
            if child.is_dir() and (child / "output/particles").is_dir():
                vrange = list((child / "output/particles").glob("PartFluid_*.vtk"))
                if vrange and child.name not in sph_runs:
                    sph_runs.append(child.name)
    return sph_runs


def read_boundary_vtk(path: Path) -> np.ndarray:
    """Read boundary particle coordinates from a binary VTK POLYDATA file."""
    if not path.exists():
        return np.zeros((0, 3), dtype=np.float32)
    data = path.read_bytes()
    position = 0

    def line() -> str:
        nonlocal position
        end = data.find(b"\n", position)
        if end < 0:
            raise ValueError("Truncated VTK header")
        val = data[position:end].rstrip(b"\r").decode("ascii", errors="replace")
        position = end + 1
        return val

    if not line().startswith("# vtk DataFile"):
        raise ValueError("Not a valid VTK file")
    line()  # title
    if line() != "BINARY" or line() != "DATASET POLYDATA":
        raise ValueError("Expected binary POLYDATA")
    header = line().split()
    if len(header) != 3 or header[0] != "POINTS":
        raise ValueError("VTK POINTS header missing")
    count = int(header[1])
    dtype = ">f4" if header[2] == "float" else ">f8"
    pts = np.frombuffer(data, dtype=dtype, count=3 * count, offset=position).reshape(count, 3).astype(np.float32)
    return pts


def calculate_pressure_kpa(density: np.ndarray, rho0: float = 1000.0, gamma: float = 7.0, c0: float = 44.29) -> np.ndarray:
    """Calculate fluid pressure in kPa using Tait's Equation of State standard in DualSPHysics.

    P = B * ((rho / rho0)^gamma - 1)
    where B = (c0^2 * rho0) / gamma
    """
    b_coeff = (c0**2 * rho0) / gamma
    ratio = np.clip(density / rho0, 0.95, 1.10)
    p_pa = b_coeff * (ratio**gamma - 1.0)
    # Clip negative pressure (cavitation threshold in weakly compressible SPH)
    p_pa = np.maximum(p_pa, 0.0)
    return (p_pa / 1000.0).astype(np.float32)  # return in kPa


def get_sph_metadata(run_dir: Path) -> dict[str, Any]:
    """Extract complete SPH metadata from actual solver outputs."""
    output_dir = run_dir / "output"
    if not output_dir.exists():
        raise FileNotFoundError(f"SPH output directory not found in {run_dir}")

    # Read input manifest if present
    manifest_path = run_dir / "input-manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}

    # Read RunPARTs.csv for time step table
    parts_csv = output_dir / "RunPARTs.csv"
    times = []
    if parts_csv.exists():
        with parts_csv.open(encoding="utf-8-sig") as file:
            parts_rows = list(csv.DictReader((l for l in file if l.strip() and not l.startswith("#")), delimiter=";"))
            times = [round(float(p["TimeStep [s]"]), 4) for p in parts_rows]

    # Find particle VTK frames
    particle_files = sorted(
        (output_dir / "particles").glob("PartFluid_*.vtk"),
        key=lambda p: int(re.search(r"(\d+)\.vtk$", p.name).group(1)) if re.search(r"(\d+)\.vtk$", p.name) else 0,
    )
    frames_count = len(particle_files)
    if frames_count == 0:
        raise ValueError("No PartFluid VTK frames found")

    if not times:
        times = [round(i * 0.01, 4) for i in range(frames_count)]

    # Read first frame to inspect initial particle count and bounds
    p0_pts, _p0_rho, _p0_vel = read_partvtk(particle_files[0])
    initial_particles_count = len(p0_pts)

    # Read boundary particles if available
    bound_path = output_dir / "CaseDambreakVal2D_Bound.vtk"
    if not bound_path.exists():
        # try any *_Bound.vtk
        bound_files = list(output_dir.glob("*_Bound.vtk"))
        if bound_files:
            bound_path = bound_files[0]

    boundary_pts = read_boundary_vtk(bound_path) if bound_path.exists() else np.zeros((0, 3), dtype=np.float32)

    # Compute bounding box
    all_x = p0_pts[:, 0]
    all_y = p0_pts[:, 1]
    all_z = p0_pts[:, 2]
    if len(boundary_pts) > 0:
        all_x = np.concatenate([all_x, boundary_pts[:, 0]])
        all_y = np.concatenate([all_y, boundary_pts[:, 1]])
        all_z = np.concatenate([all_z, boundary_pts[:, 2]])

    bounds = {
        "x_min": float(np.min(all_x)),
        "x_max": float(np.max(all_x)),
        "y_min": float(np.min(all_y)),
        "y_max": float(np.max(all_y)),
        "z_min": float(np.min(all_z)),
        "z_max": float(np.max(all_z)),
    }

    # Format boundary particles as compact flat array [x0, y0, z0, x1, y1, z1, ...]
    boundary_flat = boundary_pts.flatten().tolist()

    case_id = manifest.get("case_id", "CaseDambreakVal2D")
    classification = "LABORATORY_BENCHMARK" if "CaseDambreak" in case_id or manifest.get("input_mode") == "SYNTHETIC" else "NEAR_FIELD_DEMONSTRATION"

    return {
        "run_id": run_dir.name,
        "solver": "DualSPHysics",
        "solver_version": "5.4 CPU (LGPL-2.1)",
        "case_id": case_id,
        "classification": classification,
        "classification_badge": "LABORATORY BENCHMARK (CaseDambreakVal2D)",
        "scientific_disclaimer": "Saved laboratory tank benchmark in local coordinates; a 3D particle display does not establish a full-domain 3D river simulation or validated Ujjani prediction.",
        "particle_count": initial_particles_count,
        "boundary_particle_count": len(boundary_pts),
        "boundary_particles_flat": boundary_flat,
        "frames_count": frames_count,
        "simulation_duration_s": times[-1] if times else (frames_count - 1) * 0.01,
        "time_step_s": round(times[1] - times[0], 4) if len(times) > 1 else 0.01,
        "times": times,
        "bounds": bounds,
        "available_variables": [
            {"key": "velocity", "name": "Velocity Magnitude", "unit": "m/s", "min": 0.0, "max": 6.0},
            {"key": "elevation", "name": "Elevation (Z)", "unit": "m", "min": bounds["z_min"], "max": bounds["z_max"]},
            {"key": "pressure", "name": "Pressure (Tait EOS)", "unit": "kPa", "min": 0.0, "max": 25.0},
            {"key": "density", "name": "Fluid Density", "unit": "kg/m³", "min": 995.0, "max": 1010.0},
        ],
        "default_decimation": 1 if initial_particles_count <= 25000 else 2,
    }


def get_sph_frame(run_dir: Path, frame_index: int, decimation: int = 1) -> dict[str, Any]:
    """Read a specific particle frame and return normalized particle attributes."""
    output_dir = run_dir / "output"
    particle_files = sorted(
        (output_dir / "particles").glob("PartFluid_*.vtk"),
        key=lambda p: int(re.search(r"(\d+)\.vtk$", p.name).group(1)) if re.search(r"(\d+)\.vtk$", p.name) else 0,
    )
    if not particle_files:
        raise FileNotFoundError("No PartFluid VTK files found")

    if frame_index < 0 or frame_index >= len(particle_files):
        raise IndexError(f"Frame index {frame_index} out of range (0..{len(particle_files)-1})")

    vtk_path = particle_files[frame_index]
    pts, density, vel = read_partvtk(vtk_path)

    # Decimate if requested
    stride = max(1, int(decimation))
    if stride > 1:
        pts = pts[::stride]
        density = density[::stride]
        vel = vel[::stride]

    n_particles = len(pts)
    vx = vel[:, 0].astype(np.float32)
    vy = vel[:, 1].astype(np.float32)
    vz = vel[:, 2].astype(np.float32)
    v_mag = np.hypot(np.hypot(vx, vy), vz).astype(np.float32)
    press_kpa = calculate_pressure_kpa(density)

    # Extract time from RunPARTs.csv if present
    parts_csv = output_dir / "RunPARTs.csv"
    time_sec = frame_index * 0.01
    if parts_csv.exists():
        try:
            with parts_csv.open(encoding="utf-8-sig") as file:
                parts_rows = list(csv.DictReader((l for l in file if l.strip() and not l.startswith("#")), delimiter=";"))
                if frame_index < len(parts_rows):
                    time_sec = float(parts_rows[frame_index]["TimeStep [s]"])
        except (OSError, ValueError, KeyError) as exc:
            raise ValueError("Saved SPH timestamp table is unreadable") from exc

    # Provide both structured particle objects and high-performance flat typed arrays for Three.js
    flat_positions = pts.flatten().tolist()
    flat_velocities = v_mag.tolist()
    flat_pressures = press_kpa.tolist()
    flat_densities = density.astype(np.float32).tolist()

    # Also build classic structured particles for contract compliance
    structured_particles = [
        {
            "x": round(float(pts[i, 0]), 4),
            "y": round(float(pts[i, 1]), 4),
            "z": round(float(pts[i, 2]), 4),
            "vx": round(float(vx[i]), 4),
            "vy": round(float(vy[i]), 4),
            "vz": round(float(vz[i]), 4),
            "velocity": round(float(v_mag[i]), 4),
            "pressure": round(float(press_kpa[i]), 3),
            "density": round(float(density[i]), 2),
        }
        for i in range(n_particles)
    ]

    return {
        "frame_index": frame_index,
        "time_seconds": round(time_sec, 4),
        "particle_count": n_particles,
        "decimation_stride": stride,
        "particles": structured_particles,
        "flat_positions": flat_positions,
        "flat_velocities": flat_velocities,
        "flat_pressures": flat_pressures,
        "flat_densities": flat_densities,
        "max_velocity": float(np.max(v_mag)) if n_particles else 0.0,
        "max_pressure": float(np.max(press_kpa)) if n_particles else 0.0,
        "max_elevation": float(np.max(pts[:, 2])) if n_particles else 0.0,
    }
