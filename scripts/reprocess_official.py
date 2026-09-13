"""Validate saved native example outputs after a parser change.

This does not execute a solver or change its original execution evidence.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from damsafe.numerics.execution import save_json, sha256
from damsafe.numerics.worker import finalize

parser = argparse.ArgumentParser()
parser.add_argument("run_id")
args = parser.parse_args()
ident = str(UUID(args.run_id))
root = Path(__file__).resolve().parents[1]
directory = root / ".local/runs" / ident
original = directory / "execution.json"
record = json.loads(original.read_text(encoding="utf-8"))
if record["engine"]["engine"] != "dualsphysics":
    raise SystemExit("Only saved DualSPHysics examples are supported")
if any(stage["state"] != "SUCCEEDED" or stage["exit_code"] != 0 for stage in record["stages"]):
    raise SystemExit("Native execution stages were not all successful")
if not (directory / "output/Run.out").exists():
    raise SystemExit("Native solver output missing")
if sha256(directory / "CaseDambreakVal2D_Def.xml") != record["case"]["input_sha256"]:
    raise SystemExit("Input bytes changed after execution")
original_hash = sha256(original)
result = finalize("dualsphysics", directory, record["case"], record["engine"])
supplement = {
    "run_id": ident,
    "original_execution_manifest_sha256": original_hash,
    "native_execution_state": "SUCCEEDED",
    "postprocessing_state": "SUCCEEDED",
    "postprocessed_at": datetime.now(UTC).isoformat(),
    "automatic_execution_and_postprocessing": False,
    "reason": "Native outputs were retained; normalization was rerun after fixing parser issues",
    "case_kind": record["case"]["case_kind"],
    "input_sha256": record["case"]["input_sha256"],
    "engine_image_id": record["engine"]["image_id"],
    "frames": result["frames"],
    "cells": result["cells"],
    "normalized_sha256": result["normalized_sha256"],
    "laboratory_reference": result["laboratory_reference"],
    "diagnostics": result["diagnostics"],
}
dest = root / f"docs/evidence/phase2/dualsphysics-{ident}-postprocess.json"
save_json(dest, supplement)
print(dest)
