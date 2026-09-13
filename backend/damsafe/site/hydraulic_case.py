import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

import netCDF4
import numpy as np
from pydantic import BaseModel, Field, field_validator

from ..numerics.execution import sha256
from .preprocessing import cusecs_to_m3s, project_wgs84_to_utm43n
from .run_classifier import SiteRunAudit, SiteRunClassification, classify_site_run
from .ujjani import BHIMA_REACH, UJJANI_DAM_SPECS


class UjjaniApproximateCaseConfig(BaseModel):
    case_id: str = "ujjani_bhima_oct2020"
    event_name: str = "October 2020 Bhima River Flood"
    start_time: str = "2020-10-14T00:00:00Z"
    end_time: str = "2020-10-22T23:59:59Z"
    time_step_max_s: float = 30.0
    output_interval_s: float = 3600.0
    peak_discharge_m3s: float = 7079.2  # ~250,000 cusecs peak flood release
    baseflow_m3s: float = 150.0
    manning_channel: float = 0.035  # Literature default (Chow, 1959)
    manning_floodplain: float = 0.055  # Literature default
    downstream_stage_m: float = 443.2  # Pandharpur CWC gauge datum
    crs: str = "EPSG:32643"  # UTM Zone 43N
    vertical_datum: str = "EGM96"
    channel_approximation: Literal["TERRAIN_ONLY_CHANNEL_APPROXIMATION"] = "TERRAIN_ONLY_CHANNEL_APPROXIMATION"
    forcing_source: Literal["DIGITIZED_FROM_BULLETIN"] = "DIGITIZED_FROM_BULLETIN"
    classification: SiteRunClassification = SiteRunClassification.UJJANI_APPROXIMATE_DEMONSTRATION
    n_stream: int = 20
    n_cross: int = 4

    @field_validator("peak_discharge_m3s", "baseflow_m3s")
    @classmethod
    def validate_positive_flow(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Discharge rate cannot be negative")
        return v

    @field_validator("manning_channel", "manning_floodplain")
    @classmethod
    def validate_positive_roughness(cls, v: float) -> float:
        if v <= 0 or v > 0.5:
            raise ValueError("Manning roughness coefficient must be positive and realistic (0 < n <= 0.5)")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_time_order(cls, v: str, info) -> str:
        start = info.data.get("start_time")
        if start:
            t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if t1 <= t0:
                raise ValueError("end_time must be strictly after start_time")
        return v


def generate_oct2020_hydrograph(
    peak_m3s: float = 7079.2, baseflow_m3s: float = 150.0
) -> list[tuple[float, float]]:
    """Generate the digitized October 2020 flood release hydrograph (time in minutes, discharge in m3/s).

    Based on Maharashtra WRD flood bulletin records for Ujjani Dam during 14-22 October 2020.
    """
    if peak_m3s < 0 or baseflow_m3s < 0:
        raise ValueError("Discharge cannot be negative")

    # Time in minutes from simulation start (2020-10-14T00:00Z)
    # Total duration = 9 days = 12960 minutes
    hydrograph_points = [
        (0.0, baseflow_m3s),  # Day 0 (14 Oct 00:00)
        (720.0, baseflow_m3s * 1.5),  # Day 0 (14 Oct 12:00)
        (1440.0, 800.0),  # Day 1 (15 Oct 00:00) - Inflow surge starts
        (2160.0, 1500.0),  # Day 1 (15 Oct 12:00)
        (2880.0, 2500.0),  # Day 2 (16 Oct 00:00) - Gates opened progressively
        (3600.0, 4200.0),  # Day 2 (16 Oct 12:00)
        (4320.0, peak_m3s),  # Day 3 (17 Oct 00:00) - Peak flood release (~250k cusecs)
        (5040.0, peak_m3s * 0.95),  # Day 3 (17 Oct 12:00)
        (5760.0, 6200.0),  # Day 4 (18 Oct 00:00) - Sustained discharge
        (7200.0, 4800.0),  # Day 5 (19 Oct 00:00) - Early recession
        (8640.0, 3400.0),  # Day 6 (20 Oct 00:00) - Gates gradually lowered
        (10080.0, 1800.0),  # Day 7 (21 Oct 00:00) - Steady recession
        (11520.0, 750.0),  # Day 8 (22 Oct 00:00)
        (12960.0, 250.0),  # Day 9 (22 Oct 24:00) - Tailflow
    ]
    return [(round(t, 1), round(q, 2)) for t, q in hydrograph_points]


def _build_curvilinear_reach_netcdf(nc_path: Path, config: UjjaniApproximateCaseConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Construct a synthetic 2D UGRID-compliant netcdf grid for the Ujjani-Pandharpur Bhima reach."""
    reach = BHIMA_REACH
    waypoints = [project_wgs84_to_utm43n(lon, lat) for lon, lat in reach.key_centerline_coords_wgs84]

    n_stream = config.n_stream
    n_cross = config.n_cross

    t_orig = np.linspace(0, 1, len(waypoints))
    t_dense = np.linspace(0, 1, n_stream + 1)
    wx = np.array([p[0] for p in waypoints])
    wy = np.array([p[1] for p in waypoints])

    cx = np.interp(t_dense, t_orig, wx)
    cy = np.interp(t_dense, t_orig, wy)

    half_width = 200.0

    nodes_x = []
    nodes_y = []
    nodes_z = []

    # Elevation from ~490m at Ujjani Dam down to ~440m at Pandharpur, minus 3.5m bankfull approximation
    z_profile = np.linspace(490.0, 440.0, n_stream + 1) - 3.5

    for i in range(n_stream + 1):
        if i < n_stream:
            dx = cx[i + 1] - cx[i]
            dy = cy[i + 1] - cy[i]
        else:
            dx = cx[i] - cx[i - 1]
            dy = cy[i] - cy[i - 1]
        length = np.hypot(dx, dy) or 1.0
        nx = -dy / length
        ny = dx / length

        for j in range(n_cross + 1):
            offset = (j - (n_cross / 2.0)) * (2 * half_width / n_cross)
            px = cx[i] + nx * offset
            py = cy[i] + ny * offset
            # Center channel is deepest, banks are slightly higher
            pz = z_profile[i] + (abs(offset) / half_width) * 2.0
            nodes_x.append(px)
            nodes_y.append(py)
            nodes_z.append(pz)

    num_nodes = len(nodes_x)
    nodes_x_arr = np.array(nodes_x, dtype=np.float64)
    nodes_y_arr = np.array(nodes_y, dtype=np.float64)
    nodes_z_arr = np.array(nodes_z, dtype=np.float64)

    # Build quadrilateral elements (cells)
    elem_nodes = []
    for i in range(n_stream):
        for j in range(n_cross):
            n1 = i * (n_cross + 1) + j
            n2 = i * (n_cross + 1) + (j + 1)
            n3 = (i + 1) * (n_cross + 1) + (j + 1)
            n4 = (i + 1) * (n_cross + 1) + j
            elem_nodes.append([n1 + 1, n2 + 1, n3 + 1, n4 + 1])  # 1-indexed

    num_elems = len(elem_nodes)
    elem_nodes_arr = np.array(elem_nodes, dtype=np.int32)

    # Build unique links and identify all true boundary links
    link_to_elems = {}
    for e_idx, e in enumerate(elem_nodes):
        n1, n2, n3, n4 = e
        edges = [
            (min(n1, n2), max(n1, n2)),
            (min(n2, n3), max(n2, n3)),
            (min(n3, n4), max(n3, n4)),
            (min(n4, n1), max(n4, n1)),
        ]
        for edge in edges:
            link_to_elems.setdefault(edge, []).append(e_idx)

    links_list = sorted(list(link_to_elems.keys()))
    num_links = len(links_list)
    links_arr = np.array(links_list, dtype=np.int32)
    link_types = np.full(num_links, 2, dtype=np.int32)  # 2 = 2D link

    bnd_links = np.array(
        [idx + 1 for idx, link in enumerate(links_list) if len(link_to_elems[link]) == 1],
        dtype=np.int32,
    )

    with netCDF4.Dataset(nc_path, "w", format="NETCDF4") as ds:
        ds.createDimension("nNetNode", num_nodes)
        ds.createDimension("nNetLink", num_links)
        ds.createDimension("nNetLinkPts", 2)
        ds.createDimension("nBndLink", len(bnd_links))
        ds.createDimension("nNetElem", num_elems)
        ds.createDimension("nNetElemMaxNode", 4)

        # Coordinate System Var
        crs_var = ds.createVariable("projected_coordinate_system", "i4")
        crs_var.setncattr("name", "WGS 84 / UTM zone 43N")
        crs_var.epsg = np.int32(32643)
        crs_var.EPSG_code = "EPSG:32643"
        crs_var.grid_mapping_name = "transverse_mercator"

        # Node coordinates
        vx = ds.createVariable("NetNode_x", "f8", ("nNetNode",))
        vx.units = "m"
        vx.standard_name = "projection_x_coordinate"
        vx.grid_mapping = "projected_coordinate_system"
        vx[:] = nodes_x_arr

        vy = ds.createVariable("NetNode_y", "f8", ("nNetNode",))
        vy.units = "m"
        vy.standard_name = "projection_y_coordinate"
        vy.grid_mapping = "projected_coordinate_system"
        vy[:] = nodes_y_arr

        vz = ds.createVariable("NetNode_z", "f8", ("nNetNode",))
        vz.units = "m"
        vz.positive = "up"
        vz.standard_name = "sea_floor_depth"
        vz.grid_mapping = "projected_coordinate_system"
        vz[:] = nodes_z_arr

        # Topology
        vlink = ds.createVariable("NetLink", "i4", ("nNetLink", "nNetLinkPts"))
        vlink[:] = links_arr

        vlink_type = ds.createVariable("NetLinkType", "i4", ("nNetLink",))
        vlink_type[:] = link_types

        velem = ds.createVariable("NetElemNode", "i4", ("nNetElem", "nNetElemMaxNode"))
        velem[:] = elem_nodes_arr

        vbnd = ds.createVariable("BndLink", "i4", ("nBndLink",))
        vbnd[:] = bnd_links

    return nodes_x_arr, nodes_y_arr, nodes_z_arr, n_stream, n_cross


def build_ujjani_approximate_case(
    target: Path, config: UjjaniApproximateCaseConfig | None = None
) -> dict:
    """Prepare a complete, self-contained D-Flow FM site case for the Ujjani–Bhima reach.

    Outputs all necessary D-Flow FM input files (*.mdu, *.ext, *.bc, *.pli, *_net.nc)
    with explicit provenance and sha256 checksums.
    """
    if config is None:
        config = UjjaniApproximateCaseConfig()

    if target.exists() and any(target.iterdir()):
        raise ValueError(f"Run directory already exists and is non-empty: {target}")

    dflowfm_dir = target / "dflowfm"
    dflowfm_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate NetCDF grid
    net_nc_path = dflowfm_dir / "ujjani_net.nc"
    nodes_x, nodes_y, nodes_z, n_stream, n_cross = _build_curvilinear_reach_netcdf(net_nc_path, config)

    # 2. Upstream boundary polyline (spanning cross section at i = 0)
    up_x0, up_y0 = nodes_x[0], nodes_y[0]
    up_x1, up_y1 = nodes_x[n_cross], nodes_y[n_cross]
    up_pli_content = (
        "UpstreamDischarge\n"
        "    2    2\n"
        f" {up_x0:18.3f} {up_y0:18.3f} UpstreamDischarge_0001\n"
        f" {up_x1:18.3f} {up_y1:18.3f} UpstreamDischarge_0002\n"
    )
    (dflowfm_dir / "upstream_discharge.pli").write_text(up_pli_content, encoding="utf-8")

    # 3. Downstream boundary polyline (spanning cross section at i = n_stream)
    dn_idx0 = n_stream * (n_cross + 1)
    dn_idx1 = dn_idx0 + n_cross
    dn_x0, dn_y0 = nodes_x[dn_idx0], nodes_y[dn_idx0]
    dn_x1, dn_y1 = nodes_x[dn_idx1], nodes_y[dn_idx1]
    down_pli_content = (
        "DownstreamStage\n"
        "    2    2\n"
        f" {dn_x0:18.3f} {dn_y0:18.3f} DownstreamStage_0001\n"
        f" {dn_x1:18.3f} {dn_y1:18.3f} DownstreamStage_0002\n"
    )
    (dflowfm_dir / "downstream_stage.pli").write_text(down_pli_content, encoding="utf-8")

    # 4. Upstream discharge boundary condition (.bc)
    hydrograph = generate_oct2020_hydrograph(config.peak_discharge_m3s, config.baseflow_m3s)
    ref_time_str = "minutes since 2020-10-14 00:00:00 +00:00"

    bc_upstream_lines = [
        "[General]",
        "fileVersion           = 1.01",
        "fileType              = boundConds",
        "",
        "[Forcing]",
        "name                  = UpstreamDischarge_0001",
        "function              = timeseries",
        "time-interpolation    = linear",
        "quantity              = time",
        f"unit                  = {ref_time_str}",
        "quantity              = dischargebnd",
        "unit                  = m3/s",
    ]
    for t_min, q_m3s in hydrograph:
        bc_upstream_lines.append(f"{t_min:<10.1f} {q_m3s:<10.2f}")
    bc_upstream_lines.extend([
        "",
        "[Forcing]",
        "name                  = UpstreamDischarge_0002",
        "function              = timeseries",
        "time-interpolation    = linear",
        "quantity              = time",
        f"unit                  = {ref_time_str}",
        "quantity              = dischargebnd",
        "unit                  = m3/s",
    ])
    for t_min, q_m3s in hydrograph:
        bc_upstream_lines.append(f"{t_min:<10.1f} {q_m3s:<10.2f}")
    bc_upstream_lines.append("")
    (dflowfm_dir / "upstream_discharge.bc").write_text("\n".join(bc_upstream_lines), encoding="utf-8")

    # 5. Downstream water level boundary condition (.bc)
    bc_downstream_lines = [
        "[General]",
        "fileVersion           = 1.01",
        "fileType              = boundConds",
        "",
        "[Forcing]",
        "name                  = DownstreamStage_0001",
        "function              = timeseries",
        "time-interpolation    = linear",
        "quantity              = time",
        f"unit                  = {ref_time_str}",
        "quantity              = waterlevelbnd",
        "unit                  = m",
        f"0.0        {config.downstream_stage_m:.2f}",
        f"12960.0    {config.downstream_stage_m:.2f}",
        "",
        "[Forcing]",
        "name                  = DownstreamStage_0002",
        "function              = timeseries",
        "time-interpolation    = linear",
        "quantity              = time",
        f"unit                  = {ref_time_str}",
        "quantity              = waterlevelbnd",
        "unit                  = m",
        f"0.0        {config.downstream_stage_m:.2f}",
        f"12960.0    {config.downstream_stage_m:.2f}",
        "",
    ]
    (dflowfm_dir / "downstream_stage.bc").write_text("\n".join(bc_downstream_lines), encoding="utf-8")

    # 6. Initial water level spatial condition (bed elevation + 1.5 m initial baseflow depth)
    xyz_lines = [f"{nodes_x[i]:.3f} {nodes_y[i]:.3f} {nodes_z[i] + 1.5:.3f}" for i in range(len(nodes_x))]
    (dflowfm_dir / "initial_water_level.xyz").write_text("\n".join(xyz_lines), encoding="utf-8")

    init_ext_content = (
        "[General]\n"
        "fileVersion = 3.00\n"
        "fileType    = extForce\n\n"
        "[Spatial]\n"
        "quantity            = initialwaterlevel\n"
        "forcingFile         = initial_water_level.xyz\n"
        "forcingFileType     = sample\n"
        "interpolationMethod = triangulation\n"
    )
    (dflowfm_dir / "ujjani_init.ext").write_text(init_ext_content, encoding="utf-8")

    # 7. External boundary mapping (.ext)
    ext_content = (
        "[General]\n"
        "fileVersion = 3.00\n"
        "fileType    = extForce\n\n"
        "[Boundary]\n"
        "quantity     = dischargebnd\n"
        "locationFile = upstream_discharge.pli\n"
        "forcingFile  = upstream_discharge.bc\n\n"
        "[Boundary]\n"
        "quantity     = waterlevelbnd\n"
        "locationFile = downstream_stage.pli\n"
        "forcingFile  = downstream_stage.bc\n"
    )
    (dflowfm_dir / "ujjani_bhima.ext").write_text(ext_content, encoding="utf-8")

    # 8. Model definition file (.mdu)
    mdu_content = f"""[General]
Program                           = D-Flow FM
Version                           = Deltares, D-Flow FM1.2.184
AutoStart                         = 0
FileVersion                       = 1.02
PathsRelativeToParent             = 0

[geometry]
NetFile                           = ujjani_net.nc
IniFieldFile                      = ujjani_init.ext
BedlevType                        = 3
BedlevMode                        = 1
Conveyance2D                      = 3
Kmx                               = 0

[numerics]
CFLMax                            = 0.7
AdvecType                         = 33
Limtyphu                          = 1
Limtypmom                         = 1
Icgsolver                         = 4
TimeStepType                      = 2
Epshu                             = 0.001

[physics]
UnifFrictType                     = 1
UnifFrictCoef                     = {config.manning_channel:.4f}
Vicouv                            = 1.0
Dicouv                            = 1.0
Ag                                = 9.81

[time]
RefDate                           = 20201014
Tunit                             = S
TStart                            = 0
TStop                             = 777600
DtUser                            = 60.0
DtMax                             = 15.0
DtInit                            = 1.0

[external forcing]
ExtForceFileNew                   = ujjani_bhima.ext

[output]
HisFile                           = ujjani_bhima_his.nc
HisInterval                       = {config.output_interval_s:.1f}
MapFile                           = ujjani_bhima_map.nc
MapInterval                       = {config.output_interval_s:.1f}
RstInterval                       = 0
"""
    (dflowfm_dir / "ujjani_bhima.mdu").write_text(mdu_content, encoding="utf-8")

    # 8. DIMR root configuration (dimr_config.xml)
    dimr_xml_content = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<dimrConfig xmlns="http://schemas.deltares.nl/dimr" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://schemas.deltares.nl/dimr https://content.oss.deltares.nl/schemas/dimr-1.2.xsd">
  <documentation>
    <fileVersion>1.2</fileVersion>
    <createdBy>DamSafe Phase 5B - Ujjani Hydraulic Demonstration</createdBy>
  </documentation>
  <control>
    <start name="DFlowFM" />
  </control>
  <component name="DFlowFM">
    <library>dflowfm</library>
    <process>0</process>
    <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>
    <workingDir>dflowfm</workingDir>
    <inputFile>ujjani_bhima.mdu</inputFile>
  </component>
</dimrConfig>
"""
    (target / "dimr_config.xml").write_text(dimr_xml_content, encoding="utf-8")

    # 9. Compute file hashes for complete input lineage
    all_files = sorted([p for p in target.rglob("*") if p.is_file()])
    file_hashes = {str(p.relative_to(target).as_posix()): sha256(p) for p in all_files}

    audit = classify_site_run(
        bathymetry_type=config.channel_approximation,
        forcing_type=config.forcing_source,
    )

    manifest = {
        "case_id": config.case_id,
        "event_name": config.event_name,
        "classification": audit.classification.value,
        "is_approximate": audit.is_approximate,
        "uncertainty_disclaimer": audit.uncertainty_disclaimer,
        "blockers_for_historical_validation": audit.blockers_for_historical_validation,
        "projected_crs": config.crs,
        "vertical_datum": config.vertical_datum,
        "reach_name": BHIMA_REACH.reach_name,
        "reach_length_km": BHIMA_REACH.approximate_reach_length_km,
        "dam_specs": {
            "name": UJJANI_DAM_SPECS.name,
            "crest_elevation_m": UJJANI_DAM_SPECS.crest_elevation_m,
            "full_reservoir_level_m": UJJANI_DAM_SPECS.full_reservoir_level_m,
            "gate_count": UJJANI_DAM_SPECS.gate_count,
        },
        "simulation_parameters": {
            "start_time": config.start_time,
            "end_time": config.end_time,
            "peak_discharge_m3s": config.peak_discharge_m3s,
            "baseflow_m3s": config.baseflow_m3s,
            "manning_channel": config.manning_channel,
            "manning_floodplain": config.manning_floodplain,
            "downstream_stage_m": config.downstream_stage_m,
        },
        "input_files": file_hashes,
    }

    manifest_json_path = target / "manifest.json"
    manifest_json_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest_hash = sha256(manifest_json_path)

    return {
        "case_kind": "SITE_SCENARIO",
        "case_id": config.case_id,
        "classification": audit.classification.value,
        "is_approximate": audit.is_approximate,
        "manifest_sha256": manifest_hash,
        "input_files": file_hashes,
        "physical_case": {
            "reach": BHIMA_REACH.reach_name,
            "crs": config.crs,
            "vertical_datum": config.vertical_datum,
            "peak_discharge_m3s": config.peak_discharge_m3s,
            "start_time": config.start_time,
            "end_time": config.end_time,
            "end_time_s": 777600.0,
            "time_origin": config.start_time,
            "disclaimer": audit.uncertainty_disclaimer,
        },
    }
