from enum import StrEnum

from pydantic import BaseModel


class ExposureStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


class ExposureMetrics(BaseModel):
    category: str
    status: ExposureStatus
    dataset_provider: str | None = None
    dataset_name: str | None = None
    licence: str | None = None
    exposed_count_or_area: float | None = None
    unit: str | None = None
    notes: str


class EconomicLossResult(BaseModel):
    status: ExposureStatus = ExposureStatus.BLOCKED
    estimated_loss_inr: float | None = None
    notes: str = "Economic loss estimation is BLOCKED because traceable asset monetary valuations and verified depth-damage curves are not available in this dataset."


class ExposureAssessmentResult(BaseModel):
    run_id: str
    site_key: str
    settlements: ExposureMetrics
    population: ExposureMetrics
    farmland_ha: ExposureMetrics
    critical_facilities: ExposureMetrics
    economic_loss: EconomicLossResult


def evaluate_exposure(run_id: str, site_key: str) -> ExposureAssessmentResult:
    # Evaluate exposure datasets
    return ExposureAssessmentResult(
        run_id=run_id,
        site_key=site_key,
        settlements=ExposureMetrics(
            category="settlements",
            status=ExposureStatus.UNAVAILABLE,
            dataset_provider=None,
            dataset_name=None,
            licence=None,
            exposed_count_or_area=None,
            unit="villages/towns inundated",
            notes="DATA REQUIRED: Import a licensed settlement layer and implement a verified flood overlay before estimating exposure.",
        ),
        population=ExposureMetrics(
            category="population",
            status=ExposureStatus.UNAVAILABLE,
            dataset_provider="WorldPop / LandScan",
            dataset_name=None,
            licence=None,
            exposed_count_or_area=None,
            unit=None,
            notes="UNAVAILABLE: High-resolution population raster overlay not provided in active workspace data.",
        ),
        farmland_ha=ExposureMetrics(
            category="farmland",
            status=ExposureStatus.UNAVAILABLE,
            dataset_provider=None,
            dataset_name=None,
            licence=None,
            exposed_count_or_area=None,
            unit="hectares",
            notes="DATA REQUIRED: Import a licensed agricultural layer and implement a verified flood overlay before estimating hectares.",
        ),
        critical_facilities=ExposureMetrics(
            category="critical_facilities",
            status=ExposureStatus.UNAVAILABLE,
            dataset_provider=None,
            dataset_name=None,
            licence=None,
            exposed_count_or_area=None,
            unit=None,
            notes="UNAVAILABLE: Verified critical infrastructure location database not provided.",
        ),
        economic_loss=EconomicLossResult(),
    )
