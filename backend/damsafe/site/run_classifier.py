from enum import StrEnum

from pydantic import BaseModel, Field


class SiteRunClassification(StrEnum):
    UJJANI_APPROXIMATE_DEMONSTRATION = "UJJANI_APPROXIMATE_DEMONSTRATION"
    UJJANI_HISTORICAL_SITE_SIMULATION = "UJJANI_HISTORICAL_SITE_SIMULATION"
    ASSUMPTION_BASED_BREACH_SCENARIO = "ASSUMPTION_BASED_BREACH_SCENARIO"
    LABORATORY_BENCHMARK = "LABORATORY_BENCHMARK"
    SYNTHETIC_DEMONSTRATION = "SYNTHETIC_DEMONSTRATION"


class SiteRunAudit(BaseModel):
    classification: SiteRunClassification
    is_approximate: bool
    bathymetry_status: str
    forcing_status: str
    downstream_boundary_status: str
    roughness_status: str
    vertical_datum_status: str
    uncertainty_disclaimer: str
    blockers_for_historical_validation: list[str] = Field(default_factory=list)


def classify_site_run(
    bathymetry_type: str = "TERRAIN_ONLY_CHANNEL_APPROXIMATION",
    forcing_type: str = "DIGITIZED_FROM_BULLETIN",
    downstream_boundary_type: str = "APPROXIMATE_NORMAL_DEPTH",
    roughness_type: str = "LITERATURE_DEFAULTS",
    vertical_datum_type: str = "EGM96_UNVERIFIED_GAUGE_OFFSET",
) -> SiteRunAudit:
    """Classify a site run based on the fidelity and verification status of its physical inputs.

    A run may ONLY be classified as UJJANI_HISTORICAL_SITE_SIMULATION if all physical
    inputs (bathymetry, forcing hydrograph, downstream stage-discharge, roughness, and datum)
    are verified against field survey and continuous telemetry.

    If any input relies on approximations, literature defaults, or digitized bulletins,
    the run MUST be classified as UJJANI_APPROXIMATE_DEMONSTRATION.
    """
    blockers: list[str] = []

    if bathymetry_type != "VERIFIED_BATHYMETRY":
        blockers.append(
            f"Bathymetry is '{bathymetry_type}' (requires verified sub-surface riverbed soundings/cross-sections)."
        )

    if forcing_type != "CONTINUOUS_SCADA_TELEMETRY":
        blockers.append(
            f"Upstream forcing is '{forcing_type}' (requires continuous hourly/sub-hourly SCADA gate telemetry)."
        )

    if downstream_boundary_type != "CALIBRATED_RATING_CURVE":
        blockers.append(
            f"Downstream boundary is '{downstream_boundary_type}' (requires field-calibrated stage-discharge rating curve)."
        )

    if roughness_type != "FIELD_CALIBRATED":
        blockers.append(
            f"Roughness is '{roughness_type}' (requires hydraulic calibration against observed flood high-water marks)."
        )

    if vertical_datum_type != "SURVEYED_DATUM_TIE":
        blockers.append(
            f"Vertical datum is '{vertical_datum_type}' (requires surveyed tie between gauge zero and EGM96 geoid)."
        )

    if blockers:
        classification = SiteRunClassification.UJJANI_APPROXIMATE_DEMONSTRATION
        disclaimer = (
            "APPROXIMATE DEMONSTRATION ONLY: This hydraulic simulation uses approximate "
            "bathymetry, digitized forcing bulletins, literature roughness, and/or approximate "
            "boundary conditions. Results carry significant hydraulic uncertainty and MUST NOT "
            "be used for life-safety or emergency flood release operational decisions."
        )
        is_approximate = True
    else:
        classification = SiteRunClassification.UJJANI_HISTORICAL_SITE_SIMULATION
        disclaimer = "Validated historical simulation with field-verified physical inputs."
        is_approximate = False

    return SiteRunAudit(
        classification=classification,
        is_approximate=is_approximate,
        bathymetry_status=bathymetry_type,
        forcing_status=forcing_type,
        downstream_boundary_status=downstream_boundary_type,
        roughness_status=roughness_type,
        vertical_datum_status=vertical_datum_type,
        uncertainty_disclaimer=disclaimer,
        blockers_for_historical_validation=blockers,
    )
