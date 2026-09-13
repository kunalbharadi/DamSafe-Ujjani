"""Conservative same-grid agreement metrics; incompatible runs remain incomparable."""

import json
import math
from pathlib import Path

import netCDF4
import numpy as np

from .products import CELL_BLOCK

MAX_PAIRS = 1_000_000


def _provenance(ds):
    return json.loads(ds.provenance_json)


def _runtime(result):
    values = [s.get("elapsed_seconds") for s in result.get("stages", [])]
    return sum(v for v in values if isinstance(v, (int, float))) if values else None


def compare(first: Path, second: Path, first_product: Path, second_product: Path,
            first_run: dict, second_run: dict):
    source_a = first_run["result"].get("source_run_id") or first_run["result"].get("cached_from_run_id") or first_run["id"]
    source_b = second_run["result"].get("source_run_id") or second_run["result"].get("cached_from_run_id") or second_run["id"]
    if source_a == source_b:
        return {"state": "INCOMPATIBLE", "reasons": ["Both entries refer to the same source run"]}
    with netCDF4.Dataset(first) as a, netCDF4.Dataset(second) as b:
        pa, pb = _provenance(a), _provenance(b)
        reasons = []
        if pa.get("crs") != pb.get("crs"):
            reasons.append("CRS/local coordinate definitions differ")
        if pa.get("vertical_reference") != pb.get("vertical_reference"):
            reasons.append("Vertical datums or bed references differ")
        if pa.get("case", {}).get("case_kind") != pb.get("case", {}).get("case_kind"):
            reasons.append("Physical case and engine evidence differ")
        na, nb = len(a.dimensions["cell"]), len(b.dimensions["cell"])
        ta, tb = len(a.dimensions["time"]), len(b.dimensions["time"])
        if na != nb:
            reasons.append("Grid/column resolution differs")
        if ta != tb:
            reasons.append("Saved output-frame counts differ")
        if not reasons:
            if not np.array_equal(np.asarray(a["time"][:]), np.asarray(b["time"][:])):
                reasons.append("Saved time origins or intervals differ")
            for name in ("x", "y", "cell_area"):
                for start in range(0, na, CELL_BLOCK):
                    stop = min(na, start + CELL_BLOCK)
                    if not np.allclose(a[name][start:stop], b[name][start:stop], rtol=0, atol=1e-9):
                        reasons.append("Study domain, cell geometry or resolution differs")
                        break
                if reasons:
                    break
            if float(a.wet_threshold_m) != float(b.wet_threshold_m):
                reasons.append("Wet/dry thresholds differ")
        with netCDF4.Dataset(first_product) as ap, netCDF4.Dataset(second_product) as bp:
            if float(ap.arrival_threshold_m) != float(bp.arrival_threshold_m):
                reasons.append("Arrival/flood thresholds differ")
            if reasons:
                return {"state": "INCOMPATIBLE", "reasons": reasons,
                        "run_ids": [first_run["id"], second_run["id"]],
                        "engine_evidence": [pa.get("engine", {}).get("engine"), pb.get("engine", {}).get("engine")],
                        "cell_counts": [na, nb], "frame_counts": [ta, tb]}
            if na * ta > MAX_PAIRS:
                return {"state": "UNAVAILABLE", "reasons": ["Comparison exceeds the 1,000,000 cell-frame bounded limit"]}
            depth_sum = speed_sum = shared_area = union_area = area_delta = 0.0
            depth_weight = speed_weight = 0.0
            arrival_sum = arrival_weight = 0.0
            for start in range(0, na, CELL_BLOCK):
                stop = min(na, start + CELL_BLOCK)
                area = np.asarray(a["cell_area"][start:stop], dtype=float)
                aa = np.asarray(ap["cell_state"][start:stop], dtype=int)
                bb = np.asarray(bp["cell_state"][start:stop], dtype=int)
                both_reached = (aa == 2) & (bb == 2)
                arrival_a = np.ma.asarray(ap["arrival_elapsed_s"][start:stop]).filled(np.nan)
                arrival_b = np.ma.asarray(bp["arrival_elapsed_s"][start:stop]).filled(np.nan)
                arrival_sum += float(np.sum(area[both_reached] * np.abs(arrival_a[both_reached] - arrival_b[both_reached])))
                arrival_weight += float(np.sum(area[both_reached]))
                for i in range(ta):
                    va = np.asarray(a["valid"][i, start:stop], dtype=bool)
                    vb = np.asarray(b["valid"][i, start:stop], dtype=bool)
                    both = va & vb
                    ha = np.ma.asarray(a["h"][i, start:stop]).filled(np.nan)
                    hb = np.ma.asarray(b["h"][i, start:stop]).filled(np.nan)
                    da = both & (ha >= ap.arrival_threshold_m)
                    db = both & (hb >= bp.arrival_threshold_m)
                    shared_area += float(np.sum(area[da & db]))
                    union_area += float(np.sum(area[da | db]))
                    area_delta += float(np.sum(area[da]) - np.sum(area[db]))
                    depth_sum += float(np.sum(area[both] * (ha[both] - hb[both]) ** 2))
                    depth_weight += float(np.sum(area[both]))
                    ua = np.ma.asarray(a["u"][i, start:stop]).filled(np.nan)
                    ub = np.ma.asarray(b["u"][i, start:stop]).filled(np.nan)
                    wa = np.ma.asarray(a["v"][i, start:stop]).filled(np.nan)
                    wb = np.ma.asarray(b["v"][i, start:stop]).filled(np.nan)
                    velocities = both & np.isfinite(ua) & np.isfinite(ub) & np.isfinite(wa) & np.isfinite(wb)
                    speeds_a = np.hypot(ua[velocities], wa[velocities])
                    speeds_b = np.hypot(ub[velocities], wb[velocities])
                    speed_sum += float(np.sum(area[velocities] * (speeds_a - speeds_b) ** 2))
                    speed_weight += float(np.sum(area[velocities]))
            return {"state": "COMPARABLE", "comparison_type": "MODEL_AGREEMENT_NOT_TRUTH_ACCURACY",
                    "run_ids": [first_run["id"], second_run["id"]],
                    "engine_evidence": [pa.get("engine", {}).get("engine"), pb.get("engine", {}).get("engine")],
                    "evidence_status": [first_run["input"].get("evidence_status", "UNASSESSED"),
                                        second_run["input"].get("evidence_status", "UNASSESSED")],
                    "depth_rmse_m": math.sqrt(depth_sum / depth_weight) if depth_weight else None,
                    "velocity_magnitude_rmse_m_s": math.sqrt(speed_sum / speed_weight) if speed_weight else None,
                    "mean_extent_iou": shared_area / union_area if union_area else None,
                    "mean_flooded_area_difference_m2": area_delta / ta,
                    "mean_abs_arrival_difference_s": arrival_sum / arrival_weight if arrival_weight else None,
                    "runtime_seconds": [_runtime(first_run["result"]), _runtime(second_run["result"])],
                    "cell_count": na, "frame_count": ta,
                    "method": "area-weighted matching cells and saved frames; no resampling/interpolation"}
