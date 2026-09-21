"""Generic Scenario-to-Solver Case Builder for DamSafe.

Translates an immutable scenario snapshot and a generic SiteConfiguration into
a deterministic, fully resolved D-Flow FM case directory ready for execution.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .breach import BreachInput, BreachSensitivityVariant
from .configuration import SiteConfiguration
from .hydraulic_case import (
    UjjaniApproximateCaseConfig,
    build_ujjani_approximate_case,
)


def _parse_time_seconds(start_iso: str, end_iso: str) -> float:
    try:
        t0 = datetime.fromisoformat(start_iso)
        t1 = datetime.fromisoformat(end_iso)
        delta = (t1 - t0).total_seconds()
        return max(3600.0, delta)
    except (ValueError, TypeError):
        return 777600.0


def build_site_case(
    site_configuration: SiteConfiguration,
    scenario_snapshot: dict[str, Any],
    destination: Path,
) -> dict[str, Any]:
    """Build a complete, deterministic D-Flow FM case directory from site config and scenario snapshot.

    Parameters
    ----------
    site_configuration:
        The generic site identity, spatial CRS, terrain, hydraulic, and structure specifications.
    scenario_snapshot:
        The immutable snapshot saved when the user created/configured the scenario.
    destination:
        The target run directory where the solver input tree will be created.

    Returns
    -------
    dict
        Case metadata dictionary consumed by worker.run_stages and worker.finalize.
    """
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Target run directory already exists: {destination}")

    # Extract scenario payload from standard snapshot or raw dictionary
    scen_data = scenario_snapshot.get("scenario") or scenario_snapshot

    # 1. Determine scenario type and forcing
    forcing_data = scen_data.get("forcing") or {}
    forcing_mode = forcing_data.get("mode") if isinstance(forcing_data, dict) else None
    scen_type_raw = scen_data.get("scenario_type") or forcing_mode or "CONTROLLED_RELEASE"

    if str(scen_type_raw).upper() in {"DAM_BREACH", "COMPUTED_BREACH"}:
        scenario_type = "DAM_BREACH"
    else:
        scenario_type = "CONTROLLED_RELEASE"

    # 2. Timing
    start_time = scen_data.get("start_time") or "2020-10-14T00:00:00Z"
    end_time = scen_data.get("end_time") or "2020-10-22T23:59:59Z"
    output_interval = float(scen_data.get("output_interval_seconds") or 3600.0)

    # 3. Roughness
    manning_channel = site_configuration.hydraulic.roughness_channel_manning
    roughness_spec = scen_data.get("roughness")
    if isinstance(roughness_spec, dict) and "manning" in roughness_spec:
        try:
            manning_channel = float(roughness_spec["manning"])
        except (ValueError, TypeError):
            pass

    # 4. Downstream boundary
    downstream_stage = site_configuration.hydraulic.downstream_stage_m
    downstream_spec = scen_data.get("downstream_boundary")
    if isinstance(downstream_spec, dict) and "stage_m" in downstream_spec:
        try:
            downstream_stage = float(downstream_spec["stage_m"])
        except (ValueError, TypeError):
            pass

    # 5. Breach parameters
    breach_config = None
    if scenario_type == "DAM_BREACH":
        dam_height = site_configuration.structure.dam_height_m or 56.4
        storage_m3 = site_configuration.structure.gross_storage_capacity_m3 or 3_140_000_000.0
        breach_config = BreachInput(
            dam_height_m=dam_height,
            reservoir_volume_m3=storage_m3,
            failure_mode="OVERTOPPING",
            method="FROEHLICH_2008",
        )

    # 6. Map to case configuration
    case_config = UjjaniApproximateCaseConfig(
        case_id=scen_data.get("name") or site_configuration.identity.site_key,
        event_name=scen_data.get("name") or f"{site_configuration.identity.site_name} Scenario",
        scenario_type=scenario_type,
        breach_config=breach_config,
        breach_variant=BreachSensitivityVariant.REFERENCE,
        mode=site_configuration.terrain.terrain_mode,
        dem_paths=site_configuration.terrain.dem_paths,
        domain_width_m=site_configuration.terrain.domain_width_m,
        channel_width_m=site_configuration.terrain.channel_width_m,
        channel_bankfull_depth_m=site_configuration.terrain.channel_bankfull_depth_m,
        n_stream=site_configuration.terrain.n_stream,
        n_cross=site_configuration.terrain.n_cross,
        start_time=start_time,
        end_time=end_time,
        output_interval_s=output_interval,
        peak_discharge_m3s=site_configuration.hydraulic.default_peak_release_m3s,
        baseflow_m3s=site_configuration.hydraulic.default_baseflow_m3s,
        manning_channel=manning_channel,
        manning_floodplain=site_configuration.hydraulic.roughness_floodplain_manning,
        downstream_stage_m=downstream_stage,
        crs=site_configuration.spatial.computation_crs,
        vertical_datum=site_configuration.spatial.vertical_reference,
        centerline_wgs84=site_configuration.spatial.river_centerline_wgs84,
        reach_name=f"{site_configuration.identity.river_name} Reach",
    )

    # 7. Generate solver files in target directory
    case_metadata = build_ujjani_approximate_case(destination, case_config)

    # Attach site configuration identity and lineage
    case_metadata["site_key"] = site_configuration.identity.site_key
    case_metadata["site_name"] = site_configuration.identity.site_name
    case_metadata["river_name"] = site_configuration.identity.river_name

    return case_metadata
