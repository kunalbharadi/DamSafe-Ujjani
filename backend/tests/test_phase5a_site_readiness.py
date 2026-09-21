import pytest
from damsafe.site.preprocessing import (
    DEMMetadata,
    cusecs_to_m3s,
    ist_to_utc,
    m3s_to_cusecs,
    project_utm43n_to_wgs84,
    project_wgs84_to_utm43n,
)
from damsafe.site.readiness_gate import (
    ItemReadinessStatus,
    SiteModelVerdict,
    assess_ujjani_site_readiness,
)
from damsafe.site.ujjani import BHIMA_REACH, UJJANI_DAM_SPECS


def test_ujjani_dam_specifications():
    specs = UJJANI_DAM_SPECS
    assert specs.name == "Ujjani Dam (Bhima Dam)"
    assert specs.latitude_deg == 18.0772
    assert specs.longitude_deg == 75.1197
    assert specs.gate_count == 41
    assert specs.gate_width_m == 12.19
    assert specs.gate_height_m == 8.23
    assert specs.crest_elevation_m == 497.0
    assert specs.full_reservoir_level_m == 496.83
    assert specs.gross_storage_capacity_m3 == 3_140_000_000.0


def test_bhima_reach_definition():
    reach = BHIMA_REACH
    assert reach.reach_name == "Ujjani Dam to Pandharpur"
    assert reach.approximate_reach_length_km == 115.0
    assert reach.projected_modelling_crs == "EPSG:32643"
    assert reach.vertical_reference == "EGM96"
    assert reach.channel_geometry_type == "TERRAIN_ONLY_CHANNEL_APPROXIMATION"
    assert len(reach.key_centerline_coords_wgs84) >= 5


def test_discharge_conversion():
    # 250,000 cusecs peak flood release in October 2020
    m3s = cusecs_to_m3s(250000.0)
    assert round(m3s, 1) == 7079.2

    # Round trip
    cusec_back = m3s_to_cusecs(m3s)
    assert round(cusec_back, 0) == 250000.0

    with pytest.raises(ValueError, match="negative"):
        cusecs_to_m3s(-100.0)


def test_timezone_conversion():
    # IST is UTC+5:30
    ist_time = "2020-10-15T12:00:00"
    utc_time = ist_to_utc(ist_time)
    assert utc_time == "2020-10-15T06:30:00Z"


def test_coordinate_projections():
    lon, lat = 75.1197, 18.0772
    easting, northing = project_wgs84_to_utm43n(lon, lat)
    assert 500000 < easting < 600000
    assert 1900000 < northing < 2100000

    lon_back, lat_back = project_utm43n_to_wgs84(easting, northing)
    assert round(lon_back, 4) == round(lon, 4)
    assert round(lat_back, 4) == round(lat, 4)


def test_dem_metadata():
    dem = DEMMetadata()
    assert dem.horizontal_resolution_m == 30.0
    assert dem.native_crs == "EPSG:4326"
    assert dem.vertical_datum == "EGM96"
    assert dem.coverage_wgs84 == (74.60, 17.65, 75.95, 18.35)


def test_ujjani_readiness_gate_verdict():
    readiness = assess_ujjani_site_readiness()
    assert len(readiness.items) == 16
    assert readiness.site_key == "ujjani-bhima"
    assert readiness.mandatory_blockers_count == 1
    assert readiness.verdict == SiteModelVerdict.NOT_READY_FOR_SITE_RUN
    assert "sub-surface riverbed bathymetry" in readiness.verdict_explanation

    # Check specific items
    items_by_key = {item.key: item for item in readiness.items}
    assert items_by_key["terrain_dem"].status == ItemReadinessStatus.PASS
    assert items_by_key["dam_geometry"].status == ItemReadinessStatus.PASS
    assert items_by_key["horizontal_crs"].status == ItemReadinessStatus.PASS
    assert items_by_key["bathymetry"].status == ItemReadinessStatus.BLOCKED
    assert items_by_key["forcing"].status == ItemReadinessStatus.PARTIAL
