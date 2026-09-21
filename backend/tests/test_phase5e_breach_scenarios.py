import json
from pathlib import Path

import netCDF4
import pytest
from damsafe.numerics.adapters import capabilities, docker_argv
from damsafe.numerics.execution import Limits, execute
from damsafe.site.breach import (
    BreachInput,
    BreachMode,
    BreachSensitivityVariant,
    calculate_froehlich_2008_parameters,
    generate_breach_sensitivity_suite,
    simulate_breach_routing,
)
from damsafe.site.hydraulic_case import (
    UjjaniApproximateCaseConfig,
    build_ujjani_approximate_case,
)


def test_froehlich_2008_parameter_estimation():
    # Test nominal reservoir volume 500 MCM above breach invert, breach height 37m
    v_w = 500_000_000.0  # m3
    h_b = 37.0  # m

    # Overtopping
    b_avg_ot, tf_hr_ot, z_ot = calculate_froehlich_2008_parameters(v_w, h_b, BreachMode.OVERTOPPING)
    assert 200.0 < b_avg_ot < 350.0
    assert 1.0 < tf_hr_ot < 5.0
    assert z_ot == 1.0

    # Piping
    b_avg_pip, _tf_hr_pip, z_pip = calculate_froehlich_2008_parameters(v_w, h_b, BreachMode.PIPING)
    assert b_avg_pip < b_avg_ot  # K_o = 1.0 vs 1.3
    assert z_pip == 0.7


def test_macdonald_1984_parameter_estimation():
    from damsafe.site.breach import calculate_macdonald_1984_parameters
    v_w = 500_000_000.0  # m3
    h_w = 37.0  # m
    b_avg, t_f_hr, z_slope = calculate_macdonald_1984_parameters(v_w, h_w)
    assert b_avg > 50.0
    assert 0.5 < t_f_hr < 10.0
    assert z_slope == 0.5


def test_unsupported_breach_method_fails():
    with pytest.raises(Exception, match="Input should be"):
        BreachInput(
            method="INVALID_EXPERIMENTAL_METHOD",  # type: ignore
            gross_storage_m3=100_000_000.0,
            initial_water_level_m=490.0,
            breach_invert_elevation_m=465.0,
        )

    inp = BreachInput(
        gross_storage_m3=100_000_000.0,
        initial_water_level_m=490.0,
        breach_invert_elevation_m=465.0,
    )
    object.__setattr__(inp, "method", "INVALID_METHOD")
    with pytest.raises(ValueError, match="Unsupported breach formulation method"):
        simulate_breach_routing(inp)


def test_zero_or_negative_dt_fails():
    with pytest.raises(ValueError, match="must be strictly positive"):
        BreachInput(time_step_seconds=0.0)
    with pytest.raises(ValueError, match="must be strictly positive"):
        BreachInput(time_step_seconds=-1.0)
    with pytest.raises(ValueError, match="must be strictly positive"):
        BreachInput(simulation_duration_hours=0.0)


def test_reservoir_routing_mass_conservation():
    """Validates that level-pool reservoir routing strictly conserves fluid mass."""
    inp = BreachInput(
        gross_storage_m3=1_000_000_000.0,
        initial_water_level_m=496.83,
        breach_invert_elevation_m=465.0,
        reservoir_inflow_m3s=500.0,
        baseflow_m3s=100.0,
        simulation_duration_hours=24.0,
        time_step_seconds=5.0,
    )
    res = simulate_breach_routing(inp, BreachSensitivityVariant.REFERENCE)

    assert res.peak_discharge_m3s > 5000.0
    assert res.mass_balance_error_pct < 0.01  # < 0.01% error
    assert res.final_storage_m3 < res.initial_storage_m3
    assert len(res.hydrograph) > 100
    assert res.provenance["classification"] == "ASSUMPTION_BASED_BREACH_SCENARIO"


def test_breach_sensitivity_triad():
    """Verifies that the sensitivity suite spans a physical range of peak flows and formation rates."""
    inp = BreachInput(
        gross_storage_m3=1_500_000_000.0,
        initial_water_level_m=497.0,
        breach_invert_elevation_m=460.0,
        simulation_duration_hours=36.0,
    )
    suite = generate_breach_sensitivity_suite(inp)

    ref = suite[BreachSensitivityVariant.REFERENCE.value]
    slower = suite[BreachSensitivityVariant.SMALLER_SLOWER.value]
    faster = suite[BreachSensitivityVariant.LARGER_FASTER.value]

    # Peak discharge ordering
    assert faster.peak_discharge_m3s > ref.peak_discharge_m3s > slower.peak_discharge_m3s

    # Formation time ordering
    assert slower.formation_time_hours > ref.formation_time_hours > faster.formation_time_hours

    # All must strictly conserve mass
    assert ref.mass_balance_error_pct < 0.05
    assert slower.mass_balance_error_pct < 0.05
    assert faster.mass_balance_error_pct < 0.05


def test_breach_unphysical_input_rejection():
    """Asserts that unphysical dam or breach parameters are strictly rejected."""
    # Breach invert above crest
    with pytest.raises(ValueError, match="below dam crest"):
        BreachInput(crest_elevation_m=497.0, breach_invert_elevation_m=500.0)

    # Initial level below foundation
    with pytest.raises(ValueError, match="above foundation"):
        BreachInput(foundation_level_m=440.0, initial_water_level_m=430.0)

    # Negative storage
    with pytest.raises(ValueError, match="must be strictly positive"):
        BreachInput(gross_storage_m3=-1000.0)


def test_controlled_release_scenario_preservation(tmp_path):
    """Verifies that controlled-release scenarios remain independent and unpolluted by breach assumptions."""
    config = UjjaniApproximateCaseConfig(
        scenario_type="CONTROLLED_RELEASE",
        mode="SYNTHETIC_BENCHMARK",
        peak_discharge_m3s=5000.0,
        baseflow_m3s=200.0,
    )
    target = tmp_path / "controlled_case"
    case_dict = build_ujjani_approximate_case(target, config)

    assert case_dict["scenario_type"] == "CONTROLLED_RELEASE"
    assert case_dict["breach_simulation"] is None

    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenario_type"] == "CONTROLLED_RELEASE"
    assert manifest["breach_simulation"] is None


def test_terrain_dam_breach_dflowfm_execution(tmp_path):
    """Executes a D-Flow FM simulation driven by the computed Froehlich dam breach hydrograph."""
    dem_18 = Path("data/raw/terrain/Copernicus_DSM_COG_10_N18_00_E075_00_DEM.tif")
    dem_17 = Path("data/raw/terrain/Copernicus_DSM_COG_10_N17_00_E075_00_DEM.tif")
    if not dem_18.exists() or not dem_17.exists():
        pytest.skip("Copernicus DEM N18/N17 not present locally")

    cap = capabilities("dflowfm")
    if not cap.get("available"):
        pytest.skip(f"D-Flow FM engine unavailable: {cap.get('reason')}")

    breach_inp = BreachInput(
        gross_storage_m3=3_140_000_000.0,
        initial_water_level_m=497.0,
        breach_invert_elevation_m=465.0,
        failure_mode=BreachMode.OVERTOPPING,
        simulation_duration_hours=12.0,
    )

    config = UjjaniApproximateCaseConfig(
        scenario_type="DAM_BREACH",
        breach_config=breach_inp,
        breach_variant=BreachSensitivityVariant.REFERENCE,
        mode="TERRAIN_BASED",
        dem_paths=[dem_18, dem_17],
        domain_width_m=2000.0,
        channel_width_m=300.0,
        n_stream=10,
        n_cross=4,
        time_step_max_s=15.0,
        output_interval_s=60.0,
    )

    target = tmp_path / "breach_dflow_run"
    case_dict = build_ujjani_approximate_case(target, config)

    assert case_dict["scenario_type"] == "DAM_BREACH"
    assert case_dict["classification"] == "ASSUMPTION_BASED_BREACH_SCENARIO"
    assert case_dict["breach_simulation"] is not None
    assert case_dict["breach_simulation"]["peak_discharge_m3s"] > 10000.0

    # Shorten simulation duration for smoke execution (300s)
    mdu_path = target / "dflowfm" / "ujjani_bhima.mdu"
    mdu_text = mdu_path.read_text(encoding="utf-8")
    mdu_text = mdu_text.replace("TStop                             = 777600", "TStop                             = 300")
    mdu_text = mdu_text.replace("MapInterval                       = 3600.0", "MapInterval                       = 60.0")
    mdu_text = mdu_text.replace("HisInterval                       = 3600.0", "HisInterval                       = 60.0")
    mdu_path.write_text(mdu_text, encoding="utf-8")

    cmd = ["/delft3d/bin/run_dimr.sh", "-m", "dimr_config.xml"]
    limits = Limits(timeout_seconds=90)
    argv = docker_argv(cap["image_id"], target, cmd, limits, f"smoke-breach-dflow-{tmp_path.name}")
    res = execute(argv, target, target / "solver.log", limits, container_name=f"smoke-breach-dflow-{tmp_path.name}")

    assert res["state"] == "SUCCEEDED", f"D-Flow FM breach run failed: {res.get('error')}"

    map_nc = target / "dflowfm" / "DFM_OUTPUT_ujjani_bhima" / "ujjani_bhima_map.nc"
    assert map_nc.exists()
    with netCDF4.Dataset(map_nc) as ds:
        assert len(ds.dimensions["time"]) >= 2
