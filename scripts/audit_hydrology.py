"""Audit the original NWIC wide gate CSVs without inventing a total outflow or timezone."""

import csv
import json
import math
from collections import Counter
from datetime import datetime
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = []
for path in sorted((ROOT / "data/raw").glob("*.csv")):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)
    timestamps = [datetime.strptime(r["Data Acquisition Time"], "%d-%m-%Y %H:%M") for r in rows]  # noqa: DTZ007 -- intentionally source-local/unknown timezone
    unique = sorted(set(timestamps))
    deltas = [(b - a).total_seconds() for a, b in pairwise(unique)]
    gates = [f for f in fields if f.startswith("Gate-")]
    summary = {}
    for gate in gates:
        values, missing, invalid = [], 0, 0
        for row in rows:
            raw = row[gate]
            if raw in {"", "-", "NA", "null"}:
                missing += 1
            else:
                try:
                    val = float(raw)
                    if not math.isfinite(val) or val < 0:
                        invalid += 1
                    else:
                        values.append(val)
                except ValueError:
                    invalid += 1
        summary[gate] = {
            "missing": missing,
            "invalid": invalid,
            "nonzero": sum(v != 0 for v in values),
            "minimum": min(values, default=None),
            "maximum": max(values, default=None),
        }
    report.append(
        {
            "file": path.name,
            "rows": len(rows),
            "station": sorted({r["Station"] for r in rows}),
            "agency": sorted({r["Agency"] for r in rows}),
            "reported_coordinates": sorted({(r["Longitude"], r["Latitude"]) for r in rows}),
            "start_local_unknown_timezone": unique[0].isoformat() if unique else None,
            "end_local_unknown_timezone": unique[-1].isoformat() if unique else None,
            "duplicates": len(timestamps) - len(unique),
            "out_of_order": timestamps != sorted(timestamps),
            "interval_counts_seconds": dict(Counter(deltas)),
            "non_hourly_intervals": sum(d != 3600 for d in deltas),
            "longest_gap_hours": max(deltas, default=0) / 3600,
            "source_units": "cusec",
            "quality_flag_columns": [f for f in fields if "flag" in f.lower() or "quality" in f.lower()],
            "gates": summary,
            "total_outflow_computed": False,
            "blockers": [
                "Source timezone absent",
                "Gate-to-pathway mapping and completeness not verified",
                "Catalogue description and file units disagree",
                "Do not sum generic gate columns without structure inventory",
            ],
        }
    )
(ROOT / "docs/evidence/hydrology-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
for item in report:
    print(json.dumps({k: v for k, v in item.items() if k != "gates"}, indent=2))
