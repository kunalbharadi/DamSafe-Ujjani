from datetime import datetime

from pydantic import BaseModel

from damsafe.observation.gee import ObservationState, SatelliteObservation


class SatelliteComparisonResult(BaseModel):
    comparison_id: str
    run_id: str
    observation_id: str
    comparison_label: str = "agreement with satellite-derived flood reference"
    acquisition_time: str
    simulation_frame_time: str
    temporal_delta_hours: float = 0.0
    is_interpolated: bool = False
    crs: str = "EPSG:4326"
    resolution_deg: float
    simulation_grid_shape: tuple[int, int]
    observation_grid_shape: tuple[int, int]
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
    validation_status: str = "VALIDATED"
    notes: str = ""


def compare_simulation_with_observation(
    run_id: str,
    sim_grid: list[list[int]],
    observation: SatelliteObservation,
    sim_frame_time: str,
    resolution_deg: float = 0.005,
    is_historical_validation: bool = False,
) -> SatelliteComparisonResult:
    # 1. Require real model result
    if not sim_grid or not isinstance(sim_grid, list) or len(sim_grid) == 0 or len(sim_grid[0]) == 0:
        raise ValueError("Cannot perform validation: simulation result grid is empty or missing.")

    # 2. Block synthetic data if in historical validation mode
    if is_historical_validation and (
        observation.provenance_type == "SYNTHETIC_TEST_DATA"
        or observation.execution_state == ObservationState.SYNTHETIC_TEST_DATA
    ):
        raise ValueError(
            "Synthetic observations (SYNTHETIC_TEST_DATA) are strictly prohibited from historical validation."
        )

    # 3. Require valid observation state (OBSERVATION_READY or explicitly isolated SYNTHETIC_TEST_DATA)
    valid_states = (ObservationState.OBSERVATION_READY, ObservationState.SYNTHETIC_TEST_DATA)
    if observation.execution_state not in valid_states:
        raise ValueError(
            f"Cannot perform validation: observation is in state '{observation.execution_state}'. "
            f"Reason: {observation.notes}"
        )

    # 4. Require observation grid matrix
    obs_grid = observation.grid_matrix
    if obs_grid is None or len(obs_grid) == 0:
        raise ValueError(
            f"Cannot perform validation: observation '{observation.observation_id}' contains no raster grid matrix."
        )

    sim_rows, sim_cols = len(sim_grid), len(sim_grid[0])
    obs_rows, obs_cols = len(obs_grid), len(obs_grid[0])

    # 5. Require compatible spatial dimensions & valid geographic bounds
    if sim_rows != obs_rows or sim_cols != obs_cols:
        raise ValueError(
            f"Spatial resolution / dimension mismatch: simulation grid is ({sim_rows}x{sim_cols}) "
            f"while observation grid is ({obs_rows}x{obs_cols}). Spatial alignment required before validation."
        )

    bounds = observation.grid_bounds_wgs84
    if not bounds or len(bounds) != 4 or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise ValueError(f"Invalid geographic bounding box in observation: {bounds}")

    # 6. Timestamp alignment check (strict ISO-8601 validation)
    acq_time_str = observation.acquisition_time or observation.processing_timestamp
    try:
        t_sim = datetime.fromisoformat(sim_frame_time)
        t_obs = datetime.fromisoformat(acq_time_str)
        temporal_delta_hours = round(abs((t_sim - t_obs).total_seconds()) / 3600.0, 2)
    except (ValueError, TypeError) as err:
        raise ValueError(
            f"Invalid ISO-8601 timestamp format for comparison: sim='{sim_frame_time}', obs='{acq_time_str}'. Error: {err}"
        )

    rows, cols = sim_rows, sim_cols
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

    is_interp = temporal_delta_hours > 0.05

    return SatelliteComparisonResult(
        comparison_id=f"comp-{run_id}-{observation.observation_id}",
        run_id=run_id,
        observation_id=observation.observation_id,
        comparison_label="agreement with satellite-derived flood reference",
        acquisition_time=acq_time_str,
        simulation_frame_time=sim_frame_time,
        temporal_delta_hours=temporal_delta_hours,
        is_interpolated=is_interp,
        crs="EPSG:4326",
        resolution_deg=resolution_deg,
        simulation_grid_shape=(sim_rows, sim_cols),
        observation_grid_shape=(obs_rows, obs_cols),
        total_cells=total_cells,
        valid_comparison_cells=valid_cells,
        excluded_cells=excluded,
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
        validation_status="VALIDATED",
        notes="Evaluated strictly on valid comparison grid excluding permanent water and radar shadow/unreliable terrain.",
    )
