from datetime import datetime

from pyproj import CRS

from .contracts import ScenarioInput


def assess(project, datasets, scenario: ScenarioInput | None = None):
    missing, warnings = [], []

    def require(ok, code, message):
        if not ok:
            missing.append({"code": code, "message": message})

    bounds = project.get("verified_bounds_wgs84")
    require(
        bounds, "domain", "Verify downstream domain bounds using terrain, structures and observation stations"
    )
    projected = project.get("computation_crs")
    if projected:
        crs = CRS.from_user_input(projected)
        require(
            crs.is_projected and all(a.unit_name == "metre" for a in crs.axis_info[:2]),
            "projected_crs",
            "Select a projected computation CRS in metres from verified bounds",
        )
        if bounds and crs.area_of_use:
            w, s, e, n = crs.area_of_use.bounds
            require(
                w <= bounds[0] and s <= bounds[1] and e >= bounds[2] and n >= bounds[3],
                "crs_area",
                "Computation CRS area of use must cover the domain",
            )
    else:
        require(False, "projected_crs", "Computation CRS remains unset until bounds are verified")
    datum = project.get("vertical_reference")
    require(datum and datum.lower() != "unknown", "datum", "Establish a common elevation datum")
    for kind in ("terrain", "river"):
        require(any(d["kind"] == kind for d in datasets), kind, f"Import verified {kind} data")
    for d in datasets:
        if d["kind"] == "exposure":
            warnings.extend(d["inspection"]["issues"])
            continue
        for item in d["inspection"]["issues"]:
            missing.append({"code": item["code"], "message": f"{d['name']}: {item['message']}"})
        source_datum = d["provenance"].get("vertical_reference")
        if d["kind"] in {"terrain", "river", "structures"}:
            require(
                bool(datum and source_datum == datum),
                "datum_compatibility",
                f"{d['name']}: resolve vertical reference against project datum",
            )
        db = d["inspection"].get("bounds_wgs84")
        if db and bounds:
            intersects = (
                db[0] <= bounds[2] and db[2] >= bounds[0] and db[1] <= bounds[3] and db[3] >= bounds[1]
            )
            require(intersects, "spatial_overlap", f"{d['name']}: data does not intersect domain")
            if d["kind"] == "terrain":
                require(
                    db[0] <= bounds[0] and db[1] <= bounds[1] and db[2] >= bounds[2] and db[3] >= bounds[3],
                    "terrain_coverage",
                    "Terrain must cover the complete computation domain",
                )
    if not any(d["kind"] == "exposure" for d in datasets):
        warnings.append(
            {"code": "exposure", "message": "Impact layers unavailable; this does not block hydraulics"}
        )
    if scenario:
        for field in (
            "initial_river_state",
            "downstream_boundary",
            "tributary_inflows",
            "structure_treatment",
            "roughness",
        ):
            value = getattr(scenario, field)
            require(
                value is not None,
                field,
                f"Document {field.replace('_', ' ')} (including justified none/zero where applicable)",
            )
            if value and field in {"initial_river_state", "downstream_boundary"}:
                require(
                    bool(datum and value.vertical_reference == datum),
                    "boundary_datum",
                    f"{field}: identify compatible elevation datum",
                )
        forcing = scenario.forcing
        if forcing.mode == "prescribed_release":
            hydro = next(
                (
                    d
                    for d in datasets
                    if d["id"] == forcing.hydrograph_dataset_id and d["kind"] == "hydrology"
                ),
                None,
            )
            require(hydro, "hydrograph", "Select an imported river-outflow hydrograph in this snapshot")
            if hydro:
                info = hydro["inspection"]
                require(
                    datetime.fromisoformat(info["start_time"]) <= scenario.start_time
                    and datetime.fromisoformat(info["end_time"]) >= scenario.end_time,
                    "time_coverage",
                    "Hydrograph must cover the entire simulation period",
                )
                if forcing.historical:
                    require(
                        hydro["provenance"]["status"] != "assumed" and not hydro["provenance"]["synthetic"],
                        "historical_forcing",
                        "Historical replay requires actual observed/traceably derived forcing",
                    )
        else:
            for field in (
                "initial_level_m",
                "initial_storage_m3",
                "level_storage",
                "reservoir_inflow",
                "other_release_pathways",
                "method",
                "dam_component",
                "parameters",
            ):
                value = getattr(forcing, field)
                require(
                    value is not None and value != () and value != {},
                    f"breach_{field}",
                    f"Supply documented breach input: {field}",
                )
            require(
                False,
                "breach_method_review",
                "Phase 2 must implement and verify method applicability and reservoir balance",
            )
    else:
        require(False, "scenario", "Save a scenario to check time coverage and boundary conditions")
    # Readiness is an audit, not scientific certification. Engine preparation remains phase 2.
    require(
        False,
        "hydraulic_geometry_review",
        "Verify channel bed/cross-sections, structures and boundary placement in phase 2",
    )
    return {
        "ready_for_solver": False,
        "input_checks_pass": not missing,
        "missing": missing,
        "warnings": warnings,
        "evidence_status": "UNASSESSED",
    }
