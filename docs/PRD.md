# DamSafe Product Requirements Document

**Problem statement:** SIH 2026 PS 26161, “Dam Break Inundation Modelling Using Hydrodynamic Modelling of any River”  
**Organization:** National Technical Research Organisation (NTRO)  
**Demonstration scope:** Ujjani Dam and a bounded downstream Bhima River reach, Maharashtra  
**Status vocabulary:** `IMPLEMENTED`, `PARTIAL`, `BLOCKED`, `PLANNED`, `DEFERRED`

## Purpose and vision

DamSafe is a scenario-analysis workspace for assembling traceable inputs, running hydrodynamic models, viewing inundation products, comparing compatible model results or observations, and exporting GIS deliverables. It supports disaster-planning decisions; it is not an operational warning service.

Dam releases, breaches, and natural river blockages can produce rapid downstream flooding while the terrain, bathymetry, boundary conditions, asset inventories, and observations needed for defensible forecasts are fragmented. DamSafe makes those assumptions and evidence gaps visible. Target users are hydraulic modellers, GIS/data analysts, disaster-management operators, HADR planners, technical reviewers, and SIH judges.

## Scope and user journey

The product journey is **Dashboard → Study Area → Data Setup → Scenario Builder → Simulation → Results → Validation → Impact & HADR → Reports & Export**. A user selects a project, versions inputs, reviews readiness, freezes an immutable scenario, submits an engine run, views saved numerical output, assesses compatible evidence, and exports results.

- **Historical release:** observed, timestamped release/boundary forcing. Satellite or gauge assessment is allowed only when location, time, baseline, datum, and quality are compatible.
- **Hypothetical breach:** computed/assumed failure forcing for consequence exploration. It must never inherit an “observed-event validated” label from an unrelated flood image.

## Functional requirements

| ID | Requirement | Acceptance criterion | Status | Evidence / limitation |
|---|---|---|---|---|
| FR-001 | Projects | Create/list/read projects with explicit CRS, datum, source, and verified-bounds rules | IMPLEMENTED | `contracts.py`, project APIs |
| FR-002 | Dataset ingestion | Bounded CSV, GeoTIFF, GeoJSON, GeoPackage upload with kind, checksum, provenance, ownership validation | IMPLEMENTED | 64 MiB cap; immutable records |
| FR-003 | Data readiness | Separate missing inputs from warnings and support audit jobs | IMPLEMENTED | readiness API/worker |
| FR-004 | Scenario snapshots | Freeze project, datasets, forcing, thresholds, assumptions, and digest | IMPLEMENTED | `ScenarioInput`; DB triggers |
| FR-005 | Historical releases | Bind an aware-timestamped prescribed hydrograph | IMPLEMENTED | No complete qualified Ujjani event package yet |
| FR-006 | Hypothetical breach | Store level/storage, references, component, method, and parameters | PARTIAL | Contract and breach library exist; full API/UI-to-run integration does not |
| FR-007 | River blockage | Configure blockage formation and failure | DEFERRED | No contract or solver workflow |
| FR-008 | D-Flow FM | Queue/run/cancel, retain provenance/logs, normalize output | IMPLEMENTED | Genuine benchmark and bounded Ujjani demonstration evidence; needs installed image |
| FR-009 | DualSPHysics | Queue/run/cancel and expose saved particles | IMPLEMENTED | Genuine laboratory evidence; no full-reach Ujjani SPH claim |
| FR-010 | Flood products | Depth, velocity, arrival, duration, cell state, area; preserve dry/nodata | IMPLEMENTED | normalized/product NetCDF APIs |
| FR-011 | 2D visualization | Geographic saved cells, field/time controls, no invented interpolation | PARTIAL | Geographic centres; API has no mesh polygons |
| FR-012 | SPH visualization | Render saved x/y/z and available variables | IMPLEMENTED | Three.js + SPH frame API; near-field/lab only |
| FR-013 | Regional terrain 3D | Georeferenced regional result over terrain | PARTIAL | Three.js view exists; Cesium/authoritative terrain do not |
| FR-014 | Model comparison | Reject incompatible outputs and report common-contract differences | IMPLEMENTED | Not real-world accuracy |
| FR-015 | Sentinel-1 query/import | Preserve scene/time/orbit/method/quality; separate latest/historical | PARTIAL | Live Earth Engine execution unverified; discovery is not a flood assessment |
| FR-016 | Satellite agreement | TP/FP/FN/TN, IoU, precision, recall, F1 on compatible valid grid | BLOCKED | No qualified matching historical pair established |
| FR-017 | Gauge assessment | Stage/discharge only after station, datum, time, and quality checks | BLOCKED | API returns insufficient evidence |
| FR-018 | Exposure/HADR | Overlay verified settlements, agriculture, roads, facilities | BLOCKED | Current evaluator contains fixed demo values, not defensible overlay |
| FR-019 | Loss/population/routes | Use verified inventories and accepted methods | DEFERRED | Inputs/methods absent |
| FR-020 | Exports | GeoTIFF, Shapefile ZIP, KML, GeoJSON, CSV, HTML with provenance | IMPLEMENTED | Vector exports are cell points, not flood polygons |
| FR-021 | Recovery/isolation | Idempotency, cancellation, stale recovery, project isolation, safe paths | IMPLEMENTED | service/worker/security tests |

## Non-functional requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Immutable lineage: hashes, timestamps, units, CRS/datum, engine version, execution origin | IMPLEMENTED |
| NFR-002 | No silent real-engine fallback to mock output | IMPLEMENTED |
| NFR-003 | Accessible desktop UI at 1366×768 and 1920×1080 | PARTIAL |
| NFR-004 | Loopback local demo; authenticated authorization before public use | PARTIAL / BLOCKED publicly |
| NFR-005 | Bounded upload/query/frame/storage/worker resources | IMPLEMENTED |
| NFR-006 | Restart-safe persisted jobs/runs and explicit terminal states | IMPLEMENTED |
| NFR-007 | Performance claims measured by phase, hardware, domain; cache labelled | PARTIAL |

## MVP, success and acceptance

The MVP is a reproducible local analyst demonstration that imports validated inputs, freezes a scenario, runs or reopens genuine D-Flow FM and DualSPHysics examples, displays saved time/depth/velocity or particle output, compares compatible model output, reports missing validation/impact evidence honestly, and exports reopenable files.

Success means identity/provenance survive end to end; duplicate submissions are controlled; WET/DRY/NODATA/NOT_REACHED and observed/assumed/synthetic/imported/local states remain distinct; both engines have reproducible benchmark evidence; and no Ujjani claim exceeds `PROJECT_STATUS.md`.

Acceptance requires code plus an automated check or retained solver artifact and provenance. A skipped test, UI shell, adapter, fixture, or filename is not acceptance evidence.

## Non-goals and scientific limits

Operational forecasting, official warnings, public unauthenticated compute, generalized rainfall-runoff, natural blockage formation, debris/erosion, breach geotechnical physics, full-domain 3D SPH, automatic evacuation routing, and monetized loss are outside implemented scope.

DEM elevation is not channel bathymetry. Empirical breach routing is scenario forcing, not observed truth. Satellite flood maps have classification error and assess only compatible events. Inter-model agreement is not accuracy. The bounded Ujjani run uses approximate geometry/forcing and remains a demonstration.
