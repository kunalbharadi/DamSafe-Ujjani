from enum import StrEnum
from typing import Literal
from pydantic import BaseModel


class ItemReadinessStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class ReadinessItem(BaseModel):
    key: str
    label: str
    status: ItemReadinessStatus
    evidence: str
    limitation: str


class SiteModelVerdict(StrEnum):
    NOT_READY_FOR_SITE_RUN = "NOT_READY_FOR_SITE_RUN"
    READY_FOR_APPROXIMATE_SITE_RUN = "READY_FOR_APPROXIMATE_SITE_RUN"
    READY_FOR_HISTORICAL_SITE_RUN = "READY_FOR_HISTORICAL_SITE_RUN"


class UjjaniSiteReadinessAssessment(BaseModel):
    site_key: str = "ujjani-bhima"
    verdict: SiteModelVerdict
    verdict_explanation: str
    items: list[ReadinessItem]
    mandatory_blockers_count: int


def assess_ujjani_site_readiness(allow_approximation: bool = False) -> UjjaniSiteReadinessAssessment:
    bathymetry_item = (
        ReadinessItem(
            key="bathymetry",
            label="Sub-surface River Bathymetry",
            status=ItemReadinessStatus.PARTIAL,
            evidence="TERRAIN_ONLY_CHANNEL_APPROXIMATION: Incised trapezoidal channel (3.5m depth, 120m width) below DEM.",
            limitation="Sub-surface sounding unperformed; approximate channel carries hydraulic conveyance uncertainty.",
        )
        if allow_approximation
        else ReadinessItem(
            key="bathymetry",
            label="Sub-surface River Bathymetry",
            status=ItemReadinessStatus.BLOCKED,
            evidence="None. Public DEMs only measure water surface elevation.",
            limitation="Direct riverbed soundings/cross-sections below water level unavailable.",
        )
    )

    items = [
        ReadinessItem(
            key="terrain_dem",
            label="Terrain / DEM",
            status=ItemReadinessStatus.PASS,
            evidence="Copernicus GLO-30 30m DEM covering 74.60°E-75.95°E, 17.65°N-18.35°N.",
            limitation="30m resolution smooths micro-topography of secondary embankments.",
        ),
        ReadinessItem(
            key="channel_representation",
            label="River Channel Centerline & Reach",
            status=ItemReadinessStatus.PASS,
            evidence="115 km Bhima River reach digitized from Ujjani Dam to Pandharpur.",
            limitation="Approximate bankfull width 120m derived from satellite imagery.",
        ),
        bathymetry_item,
        ReadinessItem(
            key="dam_geometry",
            label="Dam Location & Dimensions",
            status=ItemReadinessStatus.PASS,
            evidence="WRD Maharashtra records: Lat 18.0772°N, Lon 75.1197°E, crest 497.0m, length 2,534m.",
            limitation="CAD drawing of internal dam galleried sections not public.",
        ),
        ReadinessItem(
            key="reservoir_storage",
            label="Reservoir Storage & Capacity",
            status=ItemReadinessStatus.PASS,
            evidence="Gross storage 3.14 km³ (117.24 TMC), Live 1.517 km³, Dead 1.623 km³, Area 337 km².",
            limitation="Exact sub-metre elevation-capacity rating curve requires WRD calibration.",
        ),
        ReadinessItem(
            key="hydraulic_structures",
            label="Spillway & Radial Gates",
            status=ItemReadinessStatus.PASS,
            evidence="Ogee spillway with 41 radial gates (12.19m x 8.23m).",
            limitation="Individual gate opening coefficient rating curves uncalibrated.",
        ),
        ReadinessItem(
            key="upstream_condition",
            label="Upstream Inflow & Reservoir Initial State",
            status=ItemReadinessStatus.PARTIAL,
            evidence="Daily reservoir level and aggregate inflow available from NWIC records.",
            limitation="Sub-hourly inflow time series requires hydrological routing.",
        ),
        ReadinessItem(
            key="forcing",
            label="Historical Release / Outflow Hydrograph",
            status=ItemReadinessStatus.PARTIAL,
            evidence="October 2020 aggregate daily discharge (~250,000 cusecs peak).",
            limitation="Hourly discharge breakdown across individual spillway gates unverified.",
        ),
        ReadinessItem(
            key="downstream_boundary",
            label="Downstream Hydraulic Boundary",
            status=ItemReadinessStatus.PARTIAL,
            evidence="Pandharpur river cross-section location defined.",
            limitation="Downstream stage-discharge rating curve requires field survey.",
        ),
        ReadinessItem(
            key="roughness",
            label="Manning Roughness Treatment",
            status=ItemReadinessStatus.PARTIAL,
            evidence="Bhuvan LULC estimates: Channel n=0.035, Floodplain n=0.045-0.060.",
            limitation="Spatially distributed hydraulic calibration against flood marks unperformed.",
        ),
        ReadinessItem(
            key="horizontal_crs",
            label="Horizontal Projected Coordinate System",
            status=ItemReadinessStatus.PASS,
            evidence="EPSG:32643 (UTM Zone 43N) defined and verified.",
            limitation="None.",
        ),
        ReadinessItem(
            key="vertical_datum",
            label="Vertical Elevation Reference Datum",
            status=ItemReadinessStatus.PARTIAL,
            evidence="EGM96 Geoid orthometric elevation used across DEM and dam records.",
            limitation="Local river gauge zero staff offsets to EGM96 uncalibrated.",
        ),
        ReadinessItem(
            key="simulation_clock",
            label="Simulation Clock & Timezone",
            status=ItemReadinessStatus.PASS,
            evidence="IST (UTC+5:30) to UTC ISO-8601 conversion implemented in preprocessing.",
            limitation="None.",
        ),
        ReadinessItem(
            key="permanent_water",
            label="Permanent Water Baseline Mask",
            status=ItemReadinessStatus.PASS,
            evidence="JRC Global Surface Water seasonality dataset defined for Ujjani reservoir.",
            limitation="None.",
        ),
        ReadinessItem(
            key="historical_event",
            label="Historical Event Definition",
            status=ItemReadinessStatus.PASS,
            evidence="October 2020 Bhima Flood (14-22 Oct 2020) and August 2019 event defined.",
            limitation="None.",
        ),
        ReadinessItem(
            key="satellite_observation",
            label="Sentinel-1 SAR Satellite Match",
            status=ItemReadinessStatus.PASS,
            evidence="Copernicus Sentinel-1 GRD Relative Orbit 63 pair (05 Oct vs 17 Oct 2020) identified.",
            limitation="Live cloud query requires GEE credentials in offline test environment.",
        ),
    ]

    blocked_count = sum(1 for item in items if item.status == ItemReadinessStatus.BLOCKED)
    partial_count = sum(1 for item in items if item.status == ItemReadinessStatus.PARTIAL)

    if blocked_count > 0:
        verdict = SiteModelVerdict.NOT_READY_FOR_SITE_RUN
        explanation = (
            f"Site simulation is NOT READY due to {blocked_count} blocked critical physical input (sub-surface riverbed bathymetry). "
            "Simulating the site without bathymetry will produce unphysical shallow spreading. "
            "Demonstration runs must be explicitly flagged as UJJANI_APPROXIMATE_DEMONSTRATION."
        )
    elif partial_count > 0:
        verdict = SiteModelVerdict.READY_FOR_APPROXIMATE_SITE_RUN
        explanation = (
            "Site simulation is READY FOR APPROXIMATE SITE RUN under documented channel bathymetry "
            "approximation (TERRAIN_ONLY_CHANNEL_APPROXIMATION) and digitized flood hydrograph forcing. "
            "All runs must be labelled UJJANI_APPROXIMATE_DEMONSTRATION and cannot be presented as validated historical simulations."
        )
    else:
        verdict = SiteModelVerdict.READY_FOR_HISTORICAL_SITE_RUN
        explanation = "All mandatory physical inputs verified for historical site simulation."

    return UjjaniSiteReadinessAssessment(
        site_key="ujjani-bhima",
        verdict=verdict,
        verdict_explanation=explanation,
        items=items,
        mandatory_blockers_count=blocked_count,
    )
