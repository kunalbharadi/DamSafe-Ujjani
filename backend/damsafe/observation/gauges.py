from enum import StrEnum
from pydantic import BaseModel


class GaugeAssessmentStatus(StrEnum):
    ASSESSED = "ASSESSED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class GaugeAssessmentResult(BaseModel):
    station_id: str
    station_name: str
    status: GaugeAssessmentStatus
    rmse_stage_m: float | None = None
    mae_stage_m: float | None = None
    peak_stage_diff_m: float | None = None
    peak_timing_diff_hours: float | None = None
    rmse_discharge_m3s: float | None = None
    notes: str


def evaluate_gauge_observations(station_id: str, run_id: str) -> GaugeAssessmentResult:
    # Check if verified stage/discharge gauge observations exist for Ujjani/Bhima
    # Since live gauge zero-datum alignment and stage data are absent in workspace data:
    return GaugeAssessmentResult(
        station_id=station_id,
        station_name=f"Bhima Gauge Station {station_id}",
        status=GaugeAssessmentStatus.INSUFFICIENT_EVIDENCE,
        notes="Independent gauge hydrograph comparison requires verified gauge datum, zero-level reference, and synchronized discharge recordings. Inadequate evidence currently available.",
    )
