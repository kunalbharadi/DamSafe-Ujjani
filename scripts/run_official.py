"""Run a pinned official engine example. Every invocation gets a new directory."""

import argparse
from pathlib import Path
from uuid import uuid4

from damsafe.numerics.adapters import capabilities, prepare_official, run_stages
from damsafe.numerics.execution import Limits, save_json
from damsafe.numerics.worker import finalize

parser = argparse.ArgumentParser()
parser.add_argument("engine", choices=["dualsphysics", "dflowfm"])
parser.add_argument("--particle-spacing", type=float)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
ident = str(uuid4())
dest = root / ".local/runs" / ident
capability = capabilities(args.engine)
if not capability.get("available"):
    print(capability)
    raise SystemExit(2)
case = prepare_official(args.engine, dest, args.particle_spacing)
save_json(dest / "input-manifest.json", case)
print(f"Run {ident}: {dest}", flush=True)
result = run_stages(
    args.engine, dest, ident, capability, Limits(timeout_seconds=1200, output_bytes=2_000_000_000)
)
if result["state"] == "SUCCEEDED":
    try:
        result["normalization"] = finalize(args.engine, dest, case, capability)
    except Exception as exc:  # noqa: BLE001 -- preserve normalization failure evidence
        result = {**result, "state": "FAILED", "normalization_error": str(exc)}
manifest = {
    "id": ident,
    "engine": capability,
    "case": case,
    "execution_origin": "LOCAL",
    "evidence_status": "UNASSESSED",
    **result,
}
save_json(dest / "execution.json", manifest)
save_json(root / f"docs/evidence/phase2/{args.engine}-{ident}.json", manifest)
print(f"{result['state']}: {dest}", flush=True)
raise SystemExit(0 if result["state"] == "SUCCEEDED" else 1)
