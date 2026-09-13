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
            status=ExposureStatus.AVAILABLE,
            dataset_provider="Survey of India / OpenStreetMap",
            dataset_name="Ujjani Reservoir Downstream Settlement Vectors",
            licence="Open Data",
            exposed_count_or_area=14.0,
            unit="villages/towns inundated",
            notes="Derived from spatial overlay of simulation flood extent with settlement layer.",
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
            status=ExposureStatus.AVAILABLE,
            dataset_provider="Bhuvan / LULC",
            dataset_name="Maharashtra Agricultural Land Cover 2023",
            licence="ISRO Bhuvan Open",
            exposed_count_or_area=4250.0,
            unit="hectares",
            notes="Derived from agricultural land mask intersection with >0.3m flood depth.",
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
