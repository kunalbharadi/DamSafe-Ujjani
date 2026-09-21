import math
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, field_validator


class BreachMode(StrEnum):
    OVERTOPPING = "OVERTOPPING"
    PIPING = "PIPING"


class BreachMethod(StrEnum):
    FROEHLICH_2008 = "FROEHLICH_2008"
    MACDONALD_1984 = "MACDONALD_1984"
    USER_SPECIFIED_WEIR = "USER_SPECIFIED_WEIR"


class BreachSensitivityVariant(StrEnum):
    REFERENCE = "REFERENCE"
    SMALLER_SLOWER = "SMALLER_SLOWER"
    LARGER_FASTER = "LARGER_FASTER"


class BreachInput(BaseModel):
    dam_name: str = "Ujjani Dam (Bhima Dam)"
    crest_elevation_m: float = 497.0  # WRD official crest elevation
    foundation_level_m: float = 440.6  # WRD deepest foundation level
    full_reservoir_level_m: float = 496.83  # WRD Full Reservoir Level (FRL)
    initial_water_level_m: float = 497.0  # Assumed initial reservoir level at breach onset
    gross_storage_m3: float = 3_140_000_000.0  # 3.14 km3 gross capacity
    breach_invert_elevation_m: float = 460.0  # Assumed breach bottom elevation
    failure_mode: BreachMode = BreachMode.OVERTOPPING
    method: BreachMethod = BreachMethod.FROEHLICH_2008
    storage_exponent: float = 2.5  # Reservoir stage-storage power-law shape factor
    reservoir_inflow_m3s: float = 1000.0  # Inflow during breach event
    baseflow_m3s: float = 150.0  # Downstream river baseflow
    simulation_duration_hours: float = 48.0
    time_step_seconds: float = 10.0

    # Optional direct overrides
    custom_breach_width_m: float | None = None
    custom_formation_time_hours: float | None = None
    custom_side_slope_z: float | None = None

    @field_validator("initial_water_level_m")
    @classmethod
    def validate_initial_level(cls, v: float, info) -> float:
        fnd = info.data.get("foundation_level_m", 0.0)
        if v <= fnd:
            raise ValueError(f"Initial water level ({v}m) must be above foundation ({fnd}m)")
        return v

    @field_validator("breach_invert_elevation_m")
    @classmethod
    def validate_invert_level(cls, v: float, info) -> float:
        crest = info.data.get("crest_elevation_m", 500.0)
        fnd = info.data.get("foundation_level_m", 0.0)
        if v >= crest:
            raise ValueError(f"Breach invert ({v}m) must be strictly below dam crest ({crest}m)")
        if v < fnd:
            raise ValueError(f"Breach invert ({v}m) cannot be below foundation level ({fnd}m)")
        return v

    @field_validator("gross_storage_m3", "time_step_seconds", "simulation_duration_hours")
    @classmethod
    def validate_strictly_positive(cls, v: float, info) -> float:
        if v <= 0:
            raise ValueError(f"Quantity '{info.field_name}' must be strictly positive (> 0), got {v}")
        return v

    @field_validator("reservoir_inflow_m3s", "baseflow_m3s")
    @classmethod
    def validate_non_negative(cls, v: float, info) -> float:
        if v < 0:
            raise ValueError(f"Hydraulic rate '{info.field_name}' cannot be negative, got {v}")
        return v


class BreachSimulationResult(BaseModel):
    method: BreachMethod
    failure_mode: BreachMode
    variant: BreachSensitivityVariant
    average_breach_width_m: float
    bottom_breach_width_m: float
    breach_height_m: float
    formation_time_hours: float
    side_slope_z: float
    peak_discharge_m3s: float
    time_to_peak_hours: float
    total_outflow_volume_m3: float
    initial_storage_m3: float
    final_storage_m3: float
    mass_balance_error_pct: float
    hydrograph: list[tuple[float, float]]  # (time_minutes, discharge_m3s)
    reservoir_elevation_series: list[tuple[float, float]]  # (time_minutes, level_m)
    provenance: dict


def calculate_froehlich_2008_parameters(
    volume_m3: float,
    breach_height_m: float,
    mode: BreachMode = BreachMode.OVERTOPPING,
) -> tuple[float, float, float]:
    """Calculate empirical breach parameters using Froehlich (2008).

    Equations:
      B_avg = 0.27 * K_o * V_w^0.32 * h_b^0.04
      t_f = 63.2 * sqrt(V_w / (g * h_b^2)) (in seconds)
      Z = 1.0 (overtopping) or 0.7 (piping)

    References:
      Froehlich, D. C. (2008). "Embankment dam breach parameters and their uncertainties."
      Journal of Hydraulic Engineering, 134(12), 1708-1721.
    """
    if volume_m3 <= 0 or breach_height_m <= 0:
        raise ValueError("Storage volume and breach height must be strictly positive")

    k_o = 1.3 if mode == BreachMode.OVERTOPPING else 1.0
    z_slope = 1.0 if mode == BreachMode.OVERTOPPING else 0.7
    g = 9.81

    # Average breach width (m)
    b_avg = 0.27 * k_o * (volume_m3 ** 0.32) * (breach_height_m ** 0.04)

    # Formation time (seconds -> hours)
    t_f_seconds = 63.2 * math.sqrt(volume_m3 / (g * (breach_height_m ** 2)))
    t_f_hours = t_f_seconds / 3600.0

    return b_avg, t_f_hours, z_slope


def calculate_macdonald_1984_parameters(
    volume_m3: float,
    breach_height_m: float,
    mode: BreachMode = BreachMode.OVERTOPPING,
) -> tuple[float, float, float]:
    """Calculate empirical breach parameters using MacDonald & Langridge-Monopolis (1984).

    Equations:
      V_eroded = 0.0261 * (V_w * h_w)^0.769
      t_f = 0.0179 * (V_eroded)^0.364 (in hours)
      Z = 0.5 (standard embankment side slope)
      B_avg = derived from eroded volume and height

    References:
      MacDonald, T. C., & Langridge-Monopolis, J. (1984). "Breaching characteristics of dam failures."
      Journal of Hydraulic Engineering, 110(5), 567-586.
    """
    if volume_m3 <= 0 or breach_height_m <= 0:
        raise ValueError("Storage volume and breach height must be strictly positive")

    # Volume of eroded embankment material (m3)
    v_eroded = 0.0261 * ((volume_m3 * breach_height_m) ** 0.769)
    # Formation time (hours)
    t_f_hours = 0.0179 * (v_eroded ** 0.364)
    z_slope = 0.5

    # Approximate average breach width from eroded volume
    b_avg = max(10.0, (v_eroded / max(1.0, breach_height_m ** 2)) * 0.5)

    return b_avg, t_f_hours, z_slope


def simulate_breach_routing(
    inputs: BreachInput,
    variant: BreachSensitivityVariant = BreachSensitivityVariant.REFERENCE,
) -> BreachSimulationResult:
    """Execute dynamic Level-Pool reservoir mass balance routing with Froehlich/Weir breach progression.

    Solves:
      dV/dt = Inflow(t) - (Q_breach(t, H) + Q_baseflow)
      Q_breach = C_wd * B(t) * (H - Z_b(t))^1.5 + C_side * Z * (H - Z_b(t))^2.5
      with strict conservation of mass.
    """
    h_crest = inputs.crest_elevation_m
    h_fnd = inputs.foundation_level_m
    h_frl = inputs.full_reservoir_level_m
    z_invert = inputs.breach_invert_elevation_m
    h_breach = h_crest - z_invert
    v_gross = inputs.gross_storage_m3
    alpha = inputs.storage_exponent

    # Calculate initial active volume
    h_current = inputs.initial_water_level_m
    fraction_level = max(0.0, (h_current - h_fnd) / (h_frl - h_fnd))
    v_current = v_gross * (fraction_level ** alpha)

    # Volume available above breach invert
    fraction_invert = max(0.0, (z_invert - h_fnd) / (h_frl - h_fnd))
    v_invert = v_gross * (fraction_invert ** alpha)
    v_breach_pool = max(1000.0, v_current - v_invert)

    # Determine breach geometry parameters
    if inputs.method == BreachMethod.FROEHLICH_2008:
        b_avg, t_f_hours, z_slope = calculate_froehlich_2008_parameters(
            v_breach_pool, h_breach, inputs.failure_mode
        )
    elif inputs.method == BreachMethod.MACDONALD_1984:
        b_avg, t_f_hours, z_slope = calculate_macdonald_1984_parameters(
            v_breach_pool, h_breach, inputs.failure_mode
        )
    elif inputs.method == BreachMethod.USER_SPECIFIED_WEIR:
        b_avg = inputs.custom_breach_width_m or 200.0
        t_f_hours = inputs.custom_formation_time_hours or 2.0
        z_slope = inputs.custom_side_slope_z or 1.0
    else:
        raise ValueError(f"Unsupported breach formulation method: '{inputs.method}'")

    # Apply sensitivity scaling
    if variant == BreachSensitivityVariant.SMALLER_SLOWER:
        b_avg *= 0.6
        t_f_hours *= 1.5
    elif variant == BreachSensitivityVariant.LARGER_FASTER:
        b_avg *= 1.4
        t_f_hours *= 0.7

    # Overrides if specified
    if inputs.custom_breach_width_m is not None:
        b_avg = inputs.custom_breach_width_m
    if inputs.custom_formation_time_hours is not None:
        t_f_hours = inputs.custom_formation_time_hours
    if inputs.custom_side_slope_z is not None:
        z_slope = inputs.custom_side_slope_z

    b_bottom = max(0.1 * b_avg, b_avg - z_slope * h_breach)
    t_f_seconds = max(60.0, t_f_hours * 3600.0)

    # Discharge coefficients for broad-crested weir equation (SI units)
    c_wd = 1.704  # Rectangular weir component (Cd ~ 0.57)
    c_side = 0.93  # Triangular side slope component

    dt = inputs.time_step_seconds
    total_steps = int((inputs.simulation_duration_hours * 3600.0) / dt)

    t_sec = 0.0
    v_initial = v_current
    v_total_inflow = 0.0
    v_total_outflow = 0.0

    hydrograph_points: list[tuple[float, float]] = []
    level_points: list[tuple[float, float]] = []

    peak_q = 0.0
    time_to_peak_s = 0.0

    sample_interval_s = 60.0  # Output every 1 minute
    next_sample_s = 0.0

    for step in range(total_steps + 1):
        t_sec = step * dt
        fraction_tf = min(1.0, max(0.001, t_sec / t_f_seconds))

        # Dynamic breach geometry development
        b_t = b_bottom * fraction_tf
        z_b_t = h_crest - (h_crest - z_invert) * fraction_tf

        # Calculate current water elevation from storage
        frac_v = max(0.0, v_current / v_gross)
        h_current = h_fnd + (h_frl - h_fnd) * (frac_v ** (1.0 / alpha))

        # Hydraulic head over current breach invert
        head = max(0.0, h_current - z_b_t)

        if head > 0:
            q_breach = c_wd * b_t * (head ** 1.5) + c_side * z_slope * (head ** 2.5)
        else:
            q_breach = 0.0

        q_total = q_breach + inputs.baseflow_m3s
        q_inflow = inputs.reservoir_inflow_m3s

        if q_total > peak_q:
            peak_q = q_total
            time_to_peak_s = t_sec

        # Record time series at sample interval
        if t_sec >= next_sample_s or step == total_steps:
            t_min = round(t_sec / 60.0, 1)
            hydrograph_points.append((t_min, round(q_total, 2)))
            level_points.append((t_min, round(h_current, 3)))
            next_sample_s += sample_interval_s

        # Level-pool mass balance step
        dv = (q_inflow - q_total) * dt
        v_next = max(0.0, v_current + dv)

        # Track cumulative volumes for mass conservation check
        v_total_inflow += q_inflow * dt
        v_total_outflow += q_total * dt
        v_current = v_next

    # Calculate exact mass balance residual
    # Expected outflow = (Initial Storage - Final Storage) + Total Inflow
    expected_outflow = (v_initial - v_current) + v_total_inflow
    abs_mass_error = abs(v_total_outflow - expected_outflow)
    rel_mass_error_pct = (abs_mass_error / max(1.0, v_initial)) * 100.0

    provenance = {
        "dam_name": inputs.dam_name,
        "classification": "ASSUMPTION_BASED_BREACH_SCENARIO",
        "method": inputs.method.value,
        "variant": variant.value,
        "failure_mode": inputs.failure_mode.value,
        "equations": {
            "breach_width_formula": "Froehlich (2008): B_avg = 0.27 * K_o * V_w^0.32 * h_b^0.04",
            "formation_time_formula": "Froehlich (2008): t_f = 63.2 * sqrt(V_w / (g * h_b^2))",
            "discharge_equation": "Broad-crested trapezoidal weir Q = 1.704 * B * H^1.5 + 0.93 * Z * H^2.5",
            "routing_equation": "Level-pool mass balance dV/dt = Inflow - Outflow",
        },
        "observed_dam_parameters": {
            "crest_elevation_m": inputs.crest_elevation_m,
            "full_reservoir_level_m": inputs.full_reservoir_level_m,
            "foundation_level_m": inputs.foundation_level_m,
            "gross_storage_m3": inputs.gross_storage_m3,
        },
        "assumed_breach_parameters": {
            "initial_water_level_m": inputs.initial_water_level_m,
            "breach_invert_elevation_m": inputs.breach_invert_elevation_m,
            "reservoir_inflow_m3s": inputs.reservoir_inflow_m3s,
            "baseflow_m3s": inputs.baseflow_m3s,
            "average_breach_width_m": round(b_avg, 2),
            "bottom_breach_width_m": round(b_bottom, 2),
            "formation_time_hours": round(t_f_hours, 3),
            "side_slope_z": z_slope,
        },
        "mass_conservation": {
            "initial_storage_m3": v_initial,
            "final_storage_m3": v_current,
            "total_inflow_m3": v_total_inflow,
            "total_outflow_m3": v_total_outflow,
            "mass_balance_error_pct": round(rel_mass_error_pct, 6),
        },
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "disclaimer": (
            "PROTOTYPE_BREACH_ASSUMPTION: Ujjani Dam has never suffered structural failure. "
            "This computed breach hydrograph is an empirical simulation scenario based on Froehlich (2008) "
            "and level-pool routing for disaster preparedness (HADR) exercises."
        ),
    }

    return BreachSimulationResult(
        method=inputs.method,
        failure_mode=inputs.failure_mode,
        variant=variant,
        average_breach_width_m=round(b_avg, 2),
        bottom_breach_width_m=round(b_bottom, 2),
        breach_height_m=round(h_breach, 2),
        formation_time_hours=round(t_f_hours, 3),
        side_slope_z=z_slope,
        peak_discharge_m3s=round(peak_q, 2),
        time_to_peak_hours=round(time_to_peak_s / 3600.0, 3),
        total_outflow_volume_m3=round(v_total_outflow, 2),
        initial_storage_m3=round(v_initial, 2),
        final_storage_m3=round(v_current, 2),
        mass_balance_error_pct=round(rel_mass_error_pct, 6),
        hydrograph=hydrograph_points,
        reservoir_elevation_series=level_points,
        provenance=provenance,
    )


def generate_breach_sensitivity_suite(
    inputs: BreachInput | None = None,
) -> dict[str, BreachSimulationResult]:
    """Generate the complete triad of breach sensitivity hydrographs: REFERENCE, SMALLER_SLOWER, LARGER_FASTER."""
    inputs = inputs or BreachInput()
    return {
        variant.value: simulate_breach_routing(inputs, variant)
        for variant in BreachSensitivityVariant
    }
