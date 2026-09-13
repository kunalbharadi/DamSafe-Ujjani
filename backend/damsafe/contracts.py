from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False, str_strip_whitespace=True)


class RunState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InputMode(StrEnum):
    OBSERVED = "OBSERVED"
    MIXED_ASSUMPTIONS = "MIXED_ASSUMPTIONS"
    SYNTHETIC = "SYNTHETIC"


class EvidenceStatus(StrEnum):
    UNASSESSED = "UNASSESSED"
    BENCHMARK_CHECKED = "BENCHMARK_CHECKED"
    HISTORICAL_EVENT_ASSESSED = "HISTORICAL_EVENT_ASSESSED"


class ProjectInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    site_key: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    synthetic: bool = False
    description: str = Field(default="", max_length=2000)
    verified_bounds_wgs84: tuple[float, float, float, float] | None = None
    computation_crs: str | None = None
    vertical_reference: str | None = None
    source_url: str | None = None

    @model_validator(mode="after")
    def bounds(self):
        if self.verified_bounds_wgs84:
            w, s, e, n = self.verified_bounds_wgs84
            if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
                raise ValueError("Invalid WGS84 bounds")
            if not self.source_url:
                raise ValueError("Verified bounds require a source reference")
        return self


class Provenance(Contract):
    source_url: str = Field(min_length=1, max_length=2000)
    agency: str = Field(min_length=1, max_length=300)
    licence: str = Field(min_length=1, max_length=1000)
    acquisition_date: date | None = None
    acquisition_date_note: str | None = None
    units: str = Field(min_length=1, max_length=100)
    crs: str | None = None
    vertical_reference: str | None = None
    processing_history: tuple[str, ...] = ()
    status: Literal["observed", "derived", "assumed"]
    synthetic: bool = False

    @model_validator(mode="after")
    def date_explanation(self):
        if self.acquisition_date is None and not self.acquisition_date_note:
            raise ValueError("Supply acquisition_date or an explicit missing-date note")
        return self


class HydroOptions(Contract):
    timestamp_column: str = "timestamp"
    timestamp_format: str | None = None
    value_column: str = "discharge"
    station_column: str = "station_id"
    flag_column: str = "flag"
    station_id: str
    source_timezone: str | None = None
    interval_seconds: int = Field(default=3600, gt=0)
    measurement: Literal["river_outflow", "canal_release", "reservoir_level", "unknown"]
    identity_reference: str | None = None
    accepted_flags: tuple[str, ...] = ("", "OK")


class DatasetInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["terrain", "hydrology", "river", "structures", "exposure", "roughness"]
    provenance: Provenance
    hydro: HydroOptions | None = None
    layer: str | None = None
    terrain_purpose: Literal["hydraulic", "drainage"] = "hydraulic"

    @model_validator(mode="after")
    def hydro_required(self):
        if self.kind == "hydrology" and self.hydro is None:
            raise ValueError("Hydrology requires column, station and measurement mapping")
        return self


class ReferencedInput(Contract):
    description: str = Field(min_length=1, max_length=3000)
    source_references: tuple[str, ...] = Field(min_length=1)
    status: Literal["observed", "derived", "assumed"]
    vertical_reference: str | None = None


class PrescribedRelease(Contract):
    mode: Literal["prescribed_release"]
    historical: bool
    hydrograph_dataset_id: str | None = None


class Breach(Contract):
    mode: Literal["computed_breach"]
    initial_level_m: float | None = None
    initial_storage_m3: float | None = Field(default=None, ge=0)
    level_storage: tuple[tuple[float, float], ...] = ()
    reservoir_inflow: ReferencedInput | None = None
    other_release_pathways: ReferencedInput | None = None
    method: ReferencedInput | None = None
    dam_component: ReferencedInput | None = None
    parameters: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def curve(self):
        if self.level_storage:
            if len(self.level_storage) < 2 or any(v < 0 for _, v in self.level_storage):
                raise ValueError("Storage curve needs >=2 points with nonnegative storage")
            if any(b[0] <= a[0] or b[1] <= a[1] for a, b in zip(self.level_storage, self.level_storage[1:])):
                raise ValueError("Levels and storage must be strictly increasing")
        return self


class ScenarioInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    forcing: Annotated[PrescribedRelease | Breach, Field(discriminator="mode")]
    dataset_ids: tuple[str, ...] = ()
    start_time: AwareDatetime
    end_time: AwareDatetime
    time_step_seconds: float = Field(gt=0)
    output_interval_seconds: float = Field(gt=0)
    wet_threshold_m: float = Field(gt=0)
    arrival_threshold_m: float = Field(gt=0)
    initial_river_state: ReferencedInput | None = None
    downstream_boundary: ReferencedInput | None = None
    tributary_inflows: ReferencedInput | None = None
    structure_treatment: ReferencedInput | None = None
    roughness: ReferencedInput | None = None
    assumptions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must follow start_time")
        if self.output_interval_seconds < self.time_step_seconds:
            raise ValueError("Output interval cannot be shorter than model time step")
        if self.arrival_threshold_m < self.wet_threshold_m:
            raise ValueError("Arrival threshold must be >= wet threshold")
        if len(set(self.dataset_ids)) != len(self.dataset_ids):
            raise ValueError("Duplicate dataset IDs")
        return self


class RunManifest(Contract):
    scenario_id: str
    scenario_sha256: str
    engine: Literal["dflowfm", "dualsphysics"]
    engine_version: str
    executable_sha256: str | None = None
    execution_origin: Literal["LOCAL", "IMPORTED"]
    input_mode: InputMode
    evidence_status: EvidenceStatus = EvidenceStatus.UNASSESSED
    source_references: tuple[str, ...]


class RunRequest(Contract):
    engine: Literal["dflowfm", "dualsphysics"]
    case_kind: Literal["OFFICIAL_EXAMPLE", "SITE_SCENARIO"]
    scenario_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    particle_spacing_m: Literal[0.005, 0.01, 0.02, 0.04] | None = None
