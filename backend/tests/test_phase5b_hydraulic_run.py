import json
from pathlib import Path

import netCDF4
import numpy as np
import pytest
from damsafe.numerics.adapters import prepare_ujjani_site
from damsafe.numerics.execution import sha256
from damsafe.site.hydraulic_case import (
    UjjaniApproximateCaseConfig,
    _build_curvilinear_reach_netcdf,
    build_ujjani_approximate_case,
    generate_oct2020_hydrograph,
)
from damsafe.site.readiness_gate import (
    ItemReadinessStatus,
    SiteModelVerdict,
    assess_ujjani_site_readiness,
)
from damsafe.site.run_classifier import (
    SiteRunClassification,
    classify_site_run,
)


def test_ujjani_readiness_gate_approximate_unblocked():
    # Strict mode (default): BLOCKED
    strict = assess_ujjani_site_readiness(allow_approximation=False)
    assert strict.verdict == SiteModelVerdict.NOT_READY_FOR_SITE_RUN
    assert strict.mandatory_blockers_count == 1
    items_by_key = {item.key: item for item in strict.items}
    assert items_by_key["bathymetry"].status == ItemReadinessStatus.BLOCKED

    # Approximate mode: Unlocked for approximate demonstration
    approx = assess_ujjani_site_readiness(allow_approximation=True)
    assert approx.verdict == SiteModelVerdict.READY_FOR_APPROXIMATE_SITE_RUN
    assert approx.mandatory_blockers_count == 0
    approx_items = {item.key: item for item in approx.items}
    assert approx_items["bathymetry"].status == ItemReadinessStatus.PARTIAL
    assert "TERRAIN_ONLY_CHANNEL_APPROXIMATION" in approx_items["bathymetry"].evidence
    assert "READY FOR APPROXIMATE SITE RUN" in approx.verdict_explanation


def test_site_run_classifier():
    # Default inputs: approximate
    audit_default = classify_site_run()
    assert audit_default.classification == SiteRunClassification.UJJANI_APPROXIMATE_DEMONSTRATION
    assert audit_default.is_approximate is True
    assert len(audit_default.blockers_for_historical_validation) == 5
    assert "APPROXIMATE DEMONSTRATION ONLY" in audit_default.uncertainty_disclaimer

    # Fully verified inputs: historical
    audit_verified = classify_site_run(
        bathymetry_type="VERIFIED_BATHYMETRY",
        forcing_type="CONTINUOUS_SCADA_TELEMETRY",
        downstream_boundary_type="CALIBRATED_RATING_CURVE",
        roughness_type="FIELD_CALIBRATED",
        vertical_datum_type="SURVEYED_DATUM_TIE",
    )
    assert audit_verified.classification == SiteRunClassification.UJJANI_HISTORICAL_SITE_SIMULATION
    assert audit_verified.is_approximate is False
    assert len(audit_verified.blockers_for_historical_validation) == 0

    # Partial / mixed inputs: approximate
    audit_mixed = classify_site_run(
        bathymetry_type="TERRAIN_ONLY_CHANNEL_APPROXIMATION",
        forcing_type="CONTINUOUS_SCADA_TELEMETRY",
        downstream_boundary_type="CALIBRATED_RATING_CURVE",
        roughness_type="FIELD_CALIBRATED",
        vertical_datum_type="SURVEYED_DATUM_TIE",
    )
    assert audit_mixed.classification == SiteRunClassification.UJJANI_APPROXIMATE_DEMONSTRATION
    assert audit_mixed.is_approximate is True
    assert len(audit_mixed.blockers_for_historical_validation) == 1


def test_hydraulic_case_config_validation():
    # Valid default config
    cfg = UjjaniApproximateCaseConfig()
    assert cfg.peak_discharge_m3s == 7079.2
    assert cfg.crs == "EPSG:32643"
    assert cfg.vertical_datum == "EGM96"

    # Negative peak discharge rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        UjjaniApproximateCaseConfig(peak_discharge_m3s=-10.0)

    # Negative baseflow rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        UjjaniApproximateCaseConfig(baseflow_m3s=-5.0)

    # Invalid roughness rejected
    with pytest.raises(ValueError, match="roughness"):
        UjjaniApproximateCaseConfig(manning_channel=0.0)

    with pytest.raises(ValueError, match="roughness"):
        UjjaniApproximateCaseConfig(manning_channel=0.8)

    # Invalid time order rejected
    with pytest.raises(ValueError, match="strictly after"):
        UjjaniApproximateCaseConfig(
            start_time="2020-10-20T00:00:00Z", end_time="2020-10-15T00:00:00Z"
        )


def test_oct2020_hydrograph_generation():
    hydrograph = generate_oct2020_hydrograph(peak_m3s=7079.2, baseflow_m3s=150.0)
    assert len(hydrograph) == 14
    times = [t for t, _ in hydrograph]
    discharges = [q for _, q in hydrograph]

    # Monotonically increasing time
    assert times == sorted(times)
    assert times[0] == 0.0
    assert times[-1] == 12960.0

    # Peak matches
    assert max(discharges) == 7079.2
    peak_idx = discharges.index(7079.2)
    assert times[peak_idx] == 4320.0  # Day 3

    # Negative input rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        generate_oct2020_hydrograph(peak_m3s=-100)


def test_ujjani_approximate_case_generation_and_manifest(tmp_path: Path):
    target = tmp_path / "test_case_run"
    result = build_ujjani_approximate_case(target)

    assert result["case_kind"] == "SITE_SCENARIO"
    assert result["case_id"] == "ujjani_bhima_oct2020"
    assert result["classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"
    assert result["is_approximate"] is True

    # Check generated directory structure
    dflowfm_dir = target / "dflowfm"
    assert (target / "dimr_config.xml").is_file()
    assert (dflowfm_dir / "ujjani_bhima.mdu").is_file()
    assert (dflowfm_dir / "ujjani_bhima.ext").is_file()
    assert (dflowfm_dir / "upstream_discharge.bc").is_file()
    assert (dflowfm_dir / "downstream_stage.bc").is_file()
    assert (dflowfm_dir / "upstream_discharge.pli").is_file()
    assert (dflowfm_dir / "downstream_stage.pli").is_file()
    assert (dflowfm_dir / "ujjani_net.nc").is_file()
    assert (target / "manifest.json").is_file()

    # Verify manifest and hashes
    manifest_data = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["case_id"] == "ujjani_bhima_oct2020"
    assert manifest_data["projected_crs"] == "EPSG:32643"
    assert manifest_data["vertical_datum"] == "EGM96"
    assert manifest_data["classification"] == "UJJANI_APPROXIMATE_DEMONSTRATION"

    # Verify every file hash in manifest matches actual SHA256
    for rel_path, expected_hash in manifest_data["input_files"].items():
        actual_path = target / rel_path
        assert actual_path.is_file(), f"File {rel_path} missing"
        assert sha256(actual_path) == expected_hash, f"Hash mismatch for {rel_path}"


def test_prepare_ujjani_site_via_adapters(tmp_path: Path):
    target = tmp_path / "site_run_dir"
    res = prepare_ujjani_site(target)
    assert res["case_kind"] == "SITE_SCENARIO"
    assert res["case_id"] == "ujjani_bhima_oct2020"
    assert (target / "dflowfm/ujjani_bhima.mdu").exists()

    # Rebuilding in non-empty dir raises error
    with pytest.raises(ValueError, match="already exists"):
        prepare_ujjani_site(target)


def test_reopen_and_inspect_grid_netcdf(tmp_path: Path):
    nc_path = tmp_path / "ujjani_test_net.nc"
    cfg = UjjaniApproximateCaseConfig()
    _build_curvilinear_reach_netcdf(nc_path, cfg)

    assert nc_path.is_file()
    with netCDF4.Dataset(nc_path, "r") as ds:
        assert "nNetNode" in ds.dimensions
        assert "nNetLink" in ds.dimensions
        assert "nNetElem" in ds.dimensions

        nodes_x = ds.variables["NetNode_x"][:]
        nodes_y = ds.variables["NetNode_y"][:]
        nodes_z = ds.variables["NetNode_z"][:]

        assert not np.isnan(nodes_x).any()
        assert not np.isnan(nodes_y).any()
        assert not np.isnan(nodes_z).any()
        assert not np.isinf(nodes_x).any()
        assert not np.isinf(nodes_y).any()
        assert not np.isinf(nodes_z).any()

        # Check bounds align with UTM Zone 43N (Ujjani-Pandharpur reach)
        assert 500000 < np.min(nodes_x) < 600000
        assert 1900000 < np.min(nodes_y) < 2100000

        # Bed elevation profile slopes downstream
        assert nodes_z[0] > nodes_z[-1]  # Upstream is higher than downstream
        assert 430.0 < np.min(nodes_z) < 460.0  # Pandharpur reach bed
        assert 475.0 < np.max(nodes_z) < 525.0  # Ujjani Dam reach and flanking terrain


def test_prevent_laboratory_defaults_in_site_run(tmp_path: Path):
    target = tmp_path / "site_check"
    res = build_ujjani_approximate_case(target)

    # Must NOT contain laboratory benchmarks
    assert "CaseDambreakVal2D" not in res["case_id"]
    assert "01_dflowfm_sequential" not in res["case_id"]
    assert res["case_kind"] == "SITE_SCENARIO"

    # Must specify Ujjani reach name and EPSG:32643
    assert res["physical_case"]["reach"] == "Ujjani Dam to Pandharpur"
    assert res["physical_case"]["crs"] == "EPSG:32643"
    assert res["physical_case"]["vertical_datum"] == "EGM96"

    # MDU content check
    mdu_text = (target / "dflowfm/ujjani_bhima.mdu").read_text(encoding="utf-8")
    assert "ujjani_net.nc" in mdu_text
    assert "ujjani_bhima.ext" in mdu_text
    assert "RefDate                           = 20201014" in mdu_text


def test_case_boundary_condition_files(tmp_path: Path):
    target = tmp_path / "bnd_check"
    build_ujjani_approximate_case(target)

    # Check upstream discharge file
    up_bc = (target / "dflowfm/upstream_discharge.bc").read_text(encoding="utf-8")
    assert "[Forcing]" in up_bc
    assert "dischargebnd" in up_bc
    assert "7079.2" in up_bc  # Peak flood release

    # Check downstream stage file
    down_bc = (target / "dflowfm/downstream_stage.bc").read_text(encoding="utf-8")
    assert "[Forcing]" in down_bc
    assert "waterlevelbnd" in down_bc
    assert "443.2" in down_bc  # Pandharpur stage

    # Check external forcing file
    ext = (target / "dflowfm/ujjani_bhima.ext").read_text(encoding="utf-8")
    assert "upstream_discharge.bc" in ext
    assert "downstream_stage.bc" in ext

