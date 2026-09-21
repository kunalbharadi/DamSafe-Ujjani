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
    "SiteModelVerdict",
    "SiteRunAudit",
    "SiteRunClassification",
    "UjjaniApproximateCaseConfig",
    "UjjaniDamSpecification",
    "UjjaniSiteReadinessAssessment",
    "assess_ujjani_site_readiness",
    "build_ujjani_approximate_case",
    "calculate_froehlich_2008_parameters",
    "classify_site_run",
    "cusecs_to_m3s",
    "generate_breach_sensitivity_suite",
    "generate_oct2020_hydrograph",
    "ist_to_utc",
    "m3s_to_cusecs",
    "project_utm43n_to_wgs84",
    "project_wgs84_to_utm43n",
    "sample_dem_elevations",
    "simulate_breach_routing",
]
