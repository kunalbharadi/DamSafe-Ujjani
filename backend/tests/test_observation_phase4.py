from damsafe.observation.comparison import compare_simulation_with_observation
from damsafe.observation.exposure import ExposureStatus, evaluate_exposure
from damsafe.observation.gauges import GaugeAssessmentStatus, evaluate_gauge_observations
from damsafe.observation.gee import EarthEngineService, ObservationMode, ObservationState
from damsafe.observation.import_fallback import ImportedObservationInput, import_authentic_observation


def test_earth_engine_service_query_offline():
    service = EarthEngineService()
    # With EE unconfigured, query returns either UNCONFIGURED or authentic local archive
    obs = service.query_sentinel1(
        site_key="ujjani-bhima",
        bounds_wgs84=(74.6, 18.0, 75.1, 18.4),
        mode=ObservationMode.HISTORICAL_EVENT,
        target_time="2020-10-19T00:55:11Z",
    )
    assert obs.site_key == "ujjani-bhima"
    assert obs.mode == ObservationMode.HISTORICAL_EVENT
    # If authentic local processed GeoTIFF exists, it loads authentic archive
    if obs.execution_state == ObservationState.OBSERVATION_READY:
        assert obs.provenance_type == "AUTHENTIC_IMPORTED_OBSERVATION"
        assert obs.scene_info is not None
        assert "S1A_IW_GRDH" in obs.scene_info.scene_id
        assert obs.flooded_area_km2 >= 0.0
    else:
        assert obs.execution_state in (ObservationState.UNCONFIGURED, ObservationState.AUTHENTICATION_FAILED)
        assert obs.grid_matrix is None


def test_authentic_observation_import():
    data = ImportedObservationInput(
        site_key="ujjani-bhima",
        provider_agency="ESA Copernicus / ISRO Bhuvan",
        ee_dataset_collection="COPERNICUS/S1_GRD",
        scene_ids=("S1A_IW_GRDH_1SDV_20200815T103000",),
        acquisition_time="2020-08-15T10:30:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=63,
        crs="EPSG:4326",
        resolution_m=10.0,
        processing_method="Refined_Lee_Speckle_dB_Threshold",
        threshold_db=-14.0,
        permanent_water_treatment="JRC_GSW_Masked",
        quality_mask_treatment="SRTM_HAND_Slope_Masked",
        licence="CC-BY-4.0",
        bounds_wgs84=(74.6, 18.0, 75.1, 18.4),
        matrix=[
            [0, 1, 2],
            [1, 0, 3],
            [-1, 1, 0],
        ],
    )
    obs = import_authentic_observation(data)
    assert obs.provenance_type == "AUTHENTIC_IMPORTED_OBSERVATION"
    assert obs.execution_state == ObservationState.OBSERVATION_READY
    assert obs.pixel_counts["FLOODED"] == 3
    assert obs.pixel_counts["PERMANENT_WATER"] == 1
    assert obs.pixel_counts["UNRELIABLE"] == 1
    assert obs.pixel_counts["NODATA"] == 1


def test_satellite_comparison_metrics():
    # 3x3 synthetic grid
    sim_grid = [
        [1, 1, 0],
        [0, 1, 0],
        [0, 0, 0],
    ]
    # Obs grid: 1=flooded, 0=not_flooded, 2=perm_water, 3=unreliable, -1=nodata
    obs_matrix = [
        [1, 0, 0],  # (0,0): sim 1, obs 1 -> TP; (0,1): sim 1, obs 0 -> FP; (0,2): TN
        [1, 1, 3],  # (1,0): sim 0, obs 1 -> FN; (1,1): sim 1, obs 1 -> TP; (1,2): obs 3 -> excluded
        [-1, 2, 0], # (2,0): nodata -> excluded; (2,1): perm water -> excluded; (2,2): TN
    ]
    data = ImportedObservationInput(
        site_key="ujjani-bhima",
        provider_agency="Test Provider",
        ee_dataset_collection="COPERNICUS/S1_GRD",
        scene_ids=("S1_TEST",),
        acquisition_time="2020-08-15T10:30:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=63,
        crs="EPSG:4326",
        resolution_m=10.0,
        processing_method="Test",
        threshold_db=-14.0,
        permanent_water_treatment="Masked",
        quality_mask_treatment="Masked",
        licence="Open",
        bounds_wgs84=(74.6, 18.0, 75.1, 18.4),
        matrix=obs_matrix,
    )
    obs = import_authentic_observation(data)
    res = compare_simulation_with_observation(
        run_id="run-test-123",
        sim_grid=sim_grid,
        observation=obs,
        sim_frame_time="2020-08-15T10:30:00Z",
        resolution_deg=0.01,
    )

    assert res.comparison_label == "agreement with satellite-derived flood reference"
    assert res.tp == 2
    assert res.fp == 1
    assert res.fn == 1
    assert res.tn == 2
    assert res.excluded_cells == 3
    assert res.iou == round(2 / (2 + 1 + 1), 4)  # 2/4 = 0.5
    assert res.precision == round(2 / 3, 4)       # 2/3 = 0.6667
    assert res.recall == round(2 / 3, 4)          # 2/3 = 0.6667
    assert res.f1_score == round(2 / 3, 4)        # 0.6667


def test_gauge_assessment_insufficient_evidence():
    res = evaluate_gauge_observations("station-001", "run-123")
    assert res.status == GaugeAssessmentStatus.INSUFFICIENT_EVIDENCE
    assert "Inadequate evidence" in res.notes


def test_exposure_evaluation():
    res = evaluate_exposure("run-123", "ujjani-bhima")
    assert res.settlements.status == ExposureStatus.UNAVAILABLE
    assert res.settlements.exposed_count_or_area is None
    assert res.farmland_ha.status == ExposureStatus.UNAVAILABLE
    assert res.farmland_ha.exposed_count_or_area is None
    assert res.population.status == ExposureStatus.UNAVAILABLE
    assert res.economic_loss.status == ExposureStatus.BLOCKED
    assert "BLOCKED" in res.economic_loss.notes
