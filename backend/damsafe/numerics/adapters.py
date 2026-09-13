"""Trusted official case preparation; no arbitrary uploaded scripts are executed."""

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .execution import Limits, execute, sha256

ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    "dualsphysics": {
        "directory": "DualSPHysics",
        "commit": "ef3721a861fda961f0e2f9ec4cd317b19de99086",
        "image": "damsafe-dualsphysics:5.4-cpu",
        "binary": "/opt/dualsphysics/bin/linux/DualSPHysics5.4CPU_linux64",
    },
    "dflowfm": {
        "directory": "Delft3D",
        "commit": "18f8ebb239e5a746a2ac1a7c85631b539fb15e51",
        "image": "damsafe-dflowfm:local",
        "binary": "/delft3d/bin/run_dimr.sh",
    },
}


def capabilities(engine):
    if engine not in SOURCES:
        raise ValueError("Unknown engine")
    profile = SOURCES[engine]
    if not shutil.which("docker"):
        return {"engine": engine, "available": False, "reason": "Docker executable unavailable"}
    try:
        found = subprocess.run(
            ["docker", "image", "inspect", profile["image"], "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if found.returncode:
            detail = (found.stderr or found.stdout).strip()
            daemon_down = any(
                marker in detail.lower()
                for marker in ("failed to connect", "cannot connect", "daemon is not running", "the system cannot find the file specified")
            )
            return {
                "engine": engine,
                "available": False,
                "reason": "Docker engine unavailable" if daemon_down else "Configured engine image is not installed",
                "image": profile["image"],
            }
        image_id = found.stdout.strip()
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
            raise ValueError("Docker did not return immutable image identity")
        provenance = json.loads((ROOT/"config/engine_provenance.json").read_text(encoding="utf-8")).get(engine)
        if not provenance or provenance["image_id"] != image_id:
            return {"engine":engine,"available":False,"reason":"Image identity has not been verified in engine_provenance.json"}
        return {
            "engine": engine,
            "available": True,
            "image_id": image_id,
            "image": profile["image"],
            "source_commit": profile["commit"],
            "build_provenance": provenance,
            "execution_verified": False,
            "note": "Image presence is not proof of a successful numerical run",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"engine": engine, "available": False, "reason": str(exc)}


def prepare_official(engine, target: Path, particle_spacing=None):
    source = ROOT / "external" / SOURCES[engine]["directory"]
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if commit != SOURCES[engine]["commit"]:
        raise ValueError("Source checkout is not the pinned revision")
    if target.exists():
        raise ValueError("Run directory already exists; use a new run ID")
    target.mkdir(parents=True)
    if engine == "dualsphysics":
        case = source / "examples/main/01_DamBreak/CaseDambreakVal2D_Def.xml"
        destination = target / case.name
        shutil.copyfile(case, destination)
        original_hash = sha256(destination)
        if particle_spacing is not None:
            if particle_spacing not in (0.005, 0.01, 0.02, 0.04):
                raise ValueError("Only bounded benchmark sensitivity spacings are supported")
            tree = ET.parse(destination)
            tree.find("./casedef/geometry/definition").set("dp", str(particle_spacing))
            tree.write(destination, encoding="utf-8", xml_declaration=True)
        return {
            "case_kind": "OFFICIAL_EXAMPLE" if particle_spacing is None else "BENCHMARK_SENSITIVITY",
            "case_id": "CaseDambreakVal2D",
            "source_commit": commit,
            "original_input_sha256": original_hash,
            "input_sha256": sha256(destination),
            "particle_spacing_m": particle_spacing or 0.01,
            "physical_case": {
                "domain_m": [0, 4, 0, 3],
                "initial_column_m": [0, 1, 0, 2],
                "gravity_m_s2": 9.81,
                "end_time_s": 2,
                "output_interval_s": 0.01,
                "boundaries": "closed bottom and lateral walls, free surface",
                "geometry": "2D x/z section",
            },
            "input_mode": "SYNTHETIC",
            "site": "laboratory benchmark; not Ujjani",
        }
    case = source / "examples/dflowfm/01_dflowfm_sequential"
    # Copy inputs only; no source shell scripts or batch files are run.
    shutil.copyfile(case / "dimr_config.xml", target / "dimr_config.xml")
    shutil.copytree(case / "dflowfm", target / "dflowfm")
    return {
        "case_kind": "OFFICIAL_EXAMPLE",
        "case_id": "01_dflowfm_sequential",
        "source_commit": commit,
        "input_mode": "SYNTHETIC",
        "site": "official schematic example; not Ujjani",
        "physical_case": {
            "time_origin": "1990-08-05T00:00:00+00:00",
            "end_time_s": 90000,
            "description": "25-hour schematic tidal example with open water-level boundaries",
        },
    }


def prepare_ujjani_site(target: Path, config=None):
    from ..site.hydraulic_case import UjjaniApproximateCaseConfig, build_ujjani_approximate_case

    if config is None:
        config = UjjaniApproximateCaseConfig()
    return build_ujjani_approximate_case(target, config)


def docker_argv(image_id, run_dir, command, limits, name):
    return [
        "docker",
        "run",
        "--name",
        name,
        "--network",
        "none",
        "--cpus",
        str(limits.cpus),
        "--memory",
        f"{limits.memory_mb}m",
        "--memory-swap",
        f"{limits.memory_mb}m",
        "--pids-limit",
        "128",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=128m",
        "--mount",
        f"type=bind,source={run_dir.resolve()},target=/work",
        "--workdir",
        "/work",
        "--env",
        f"OMP_NUM_THREADS={limits.cpus}",
        image_id,
        *command,
    ]


def run_stages(
    engine, run_dir, run_id, capability, limits: Limits, cancelled=lambda: False, progress=lambda _: None
):
    if not capability.get("available"):
        return {"state": "FAILED", "reason": capability.get("reason", "Engine unavailable"), "stages": []}
    if not re.fullmatch(r"[a-f0-9-]{36}", run_id):
        raise ValueError("Invalid run ID")
    if engine == "dualsphysics":
        commands = [
            (
                "prepare",
                ["GenCase_linux64", "CaseDambreakVal2D_Def", "output/CaseDambreakVal2D", "-save:all"],
            ),
            (
                "solver",
                [
                    "DualSPHysics5.4CPU_linux64",
                    "output/CaseDambreakVal2D",
                    "output",
                    f"-ompthreads:{limits.cpus}",
                ],
            ),
            (
                "particles",
                [
                    "PartVTK_linux64",
                    "-dirdata",
                    "output/data",
                    "-savevtk",
                    "output/particles/PartFluid",
                    "-onlytype:-all,fluid",
                    "-vars:+idp,+vel,+rhop",
                ],
            ),
        ]
    else:
        # Official run_example.sh invokes run_dimr.sh -m dimr_config.xml for a single process.
        commands = [("solver", ["/delft3d/bin/run_dimr.sh", "-m", "dimr_config.xml"])]
    outcomes = []
    for stage, command in commands:
        name = f"damsafe-{run_id}-{stage}"
        result = execute(
            docker_argv(capability["image_id"], run_dir, command, limits, name),
            run_dir,
            run_dir / f"{stage}.log",
            limits,
            cancelled,
            lambda p, stage=stage: progress({"stage": stage, **p}),
            name,
        )
        outcomes.append({"stage": stage, **result})
        if result["state"] != "SUCCEEDED":
            return {"state": result["state"], "stages": outcomes}
    if engine == "dualsphysics":
        if not list((run_dir / "output/data").glob("Part_*.bi4")) or not list(
            (run_dir / "output/particles").glob("*.vtk")
        ):
            return {
                "state": "FAILED",
                "reason": "Solver returned zero without required numerical output",
                "stages": outcomes,
            }
    else:
        if not list(run_dir.rglob("*_map.nc")):
            return {"state": "FAILED", "reason": "Missing D-Flow map output", "stages": outcomes}
        if re.search(r"(?m)^\*\* ERROR\s*:", (run_dir / "solver.log").read_text(encoding="utf-8", errors="replace")):
            return {"state": "FAILED", "reason": "D-Flow native log reports a solver error", "stages": outcomes}
    return {"state": "SUCCEEDED", "stages": outcomes}
