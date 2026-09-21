"""DamSafe Phase 5 Ujjani Site Data, Model Readiness & Hydraulic Demonstration Package."""

from .breach import (
    BreachInput,
    BreachMethod,
    BreachMode,
    BreachSensitivityVariant,
    BreachSimulationResult,
    calculate_froehlich_2008_parameters,
    generate_breach_sensitivity_suite,
    simulate_breach_routing,
)
from .case_builder import build_site_case
from .configuration import (
    SiteConfiguration,
    SiteHydraulic,
    SiteIdentity,
    SiteSpatial,
    SiteStructure,
    SiteTerrain,
    get_ujjani_site_configuration,
    load_site_configuration,
)
from .hydraulic_case import (
    UjjaniApproximateCaseConfig,
    build_ujjani_approximate_case,
    generate_oct2020_hydrograph,
)
from .preprocessing import (
    ChannelApproximationResult,
    DEMMetadata,
    cusecs_to_m3s,
    ist_to_utc,
    m3s_to_cusecs,
    project_utm43n_to_wgs84,
    project_wgs84_to_utm43n,
)
from .readiness_gate import (
    ItemReadinessStatus,
    ReadinessItem,
    SiteModelVerdict,
    UjjaniSiteReadinessAssessment,
    assess_ujjani_site_readiness,
)
from .run_classifier import (
    SiteRunAudit,
    SiteRunClassification,
    classify_site_run,
)
from .terrain_sampler import (
    DEMProvenance,
    IncompatibleTerrainError,
    MissingTerrainError,
    sample_dem_elevations,
)
from .ujjani import (
    BHIMA_REACH,
    UJJANI_DAM_SPECS,
    BhimaReachDefinition,
    UjjaniDamSpecification,
)

__all__ = [
    "BHIMA_REACH",
    "UJJANI_DAM_SPECS",
    "BhimaReachDefinition",
    "BreachInput",
    "BreachMethod",
    "BreachMode",
    "BreachSensitivityVariant",
    "BreachSimulationResult",
    "ChannelApproximationResult",
    "DEMMetadata",
    "DEMProvenance",
    "IncompatibleTerrainError",
    "ItemReadinessStatus",
    "MissingTerrainError",
    "ReadinessItem",
    "SiteConfiguration",
    "SiteHydraulic",
    "SiteIdentity",
    "SiteModelVerdict",
    "SiteRunAudit",
    "SiteRunClassification",
    "SiteSpatial",
    "SiteStructure",
    "SiteTerrain",
    "UjjaniApproximateCaseConfig",
    "UjjaniDamSpecification",
    "UjjaniSiteReadinessAssessment",
    "assess_ujjani_site_readiness",
    "build_site_case",
    "build_ujjani_approximate_case",
    "calculate_froehlich_2008_parameters",
    "classify_site_run",
    "cusecs_to_m3s",
    "generate_breach_sensitivity_suite",
    "generate_oct2020_hydrograph",
    "get_ujjani_site_configuration",
    "ist_to_utc",
    "load_site_configuration",
    "m3s_to_cusecs",
    "project_utm43n_to_wgs84",
    "project_wgs84_to_utm43n",
    "sample_dem_elevations",
    "simulate_breach_routing",
]
