from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel
from damsafe.observation.gee import SatelliteObservation


class SatelliteComparisonResult(BaseModel):
    comparison_id: str
    run_id: str
    observation_id: str
    comparison_label: str = "agreement with satellite-derived flood reference"
    acquisition_time: str
    simulation_frame_time: str
    is_interpolated: bool = False
    crs: str = "EPSG:4326"
    resolution_deg: float
    total_cells: int
    valid_comparison_cells: int
    excluded_cells: int
    tp: int
    fp: int
    fn: int
    tn: int
    iou: float
    precision: float
    recall: float
    f1_score: float
    simulated_flooded_area_km2: float
    observed_flooded_area_km2: float
    absolute_area_diff_km2: float
    relative_area_diff_pct: float | None = None
    notes: str = ""


def compare_simulation_with_observation(
    run_id: str,
    sim_grid: list[list[int]],
    observation: SatelliteObservation,
    sim_frame_time: str,
    resolution_deg: float = 0.005,
) -> SatelliteComparisonResult:
    obs_grid = observation.grid_matrix or []
    rows = min(len(sim_grid), len(obs_grid))
    cols = min(len(sim_grid[0]), len(obs_grid[0])) if rows > 0 else 0

    tp = fp = fn = tn = excluded = 0
    dx = dy = resolution_deg
    cell_area_km2 = (dx * 111.0) * (dy * 111.0)

    for r in range(rows):
        for c in range(cols):
            s_val = sim_grid[r][c]
            o_val = obs_grid[r][c]

            # Exclude nodata (-1), permanent water (2), unreliable (3)
            if s_val < 0 or o_val < 0 or o_val in (2, 3):
                excluded += 1
                continue

            s_wet = 1 if s_val > 0 else 0
            o_wet = 1 if o_val == 1 else 0

            if s_wet == 1 and o_wet == 1:
                tp += 1
            elif s_wet == 1 and o_wet == 0:
                fp += 1
            elif s_wet == 0 and o_wet == 1:
                fn += 1
            else:
                tn += 1

    valid_cells = tp + fp + fn + tn
    total_cells = rows * cols

    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else (1.0 if (tp == 0 and fp == 0 and fn == 0) else 0.0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    sim_area = (tp + fp) * cell_area_km2
    obs_area = (tp + fn) * cell_area_km2
    abs_diff = abs(sim_area - obs_area)
    rel_diff = (abs_diff / obs_area * 100.0) if obs_area > 0 else None

    is_interp = sim_frame_time != observation.acquisition_time

    return SatelliteComparisonResult(
        comparison_id=f"comp-{run_id}-{observation.observation_id}",
        run_id=run_id,
        observation_id=observation.observation_id,
        comparison_label="agreement with satellite-derived flood reference",
        acquisition_time=observation.acquisition_time,
        simulation_frame_time=sim_frame_time,
        is_interpolated=is_interp,
        crs="EPSG:4326",
        resolution_deg=resolution_deg,
        total_cells=total_cells,
        valid_comparison_cells=valid_cells,
        excluded_cells=excluded + (total_cells - valid_cells - excluded),
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        iou=round(iou, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        simulated_flooded_area_km2=round(sim_area, 2),
        observed_flooded_area_km2=round(obs_area, 2),
        absolute_area_diff_km2=round(abs_diff, 2),
        relative_area_diff_pct=round(rel_diff, 2) if rel_diff is not None else None,
        notes="Evaluated strictly on valid comparison grid excluding permanent water and radar shadow/unreliable terrain.",
    )
