# Data manifest — Phase 5A Ujjani site data, 2026-09-13

## Phase 5A Ujjani site data acquisition

Phase 5A adds authoritative Ujjani Dam and Bhima River reach specifications codified in `backend/damsafe/site/ujjani.py`, preprocessing utilities in `backend/damsafe/site/preprocessing.py`, and a formal 16-item model-readiness gate in `backend/damsafe/site/readiness_gate.py`.

The complete dataset catalogue covering terrain (Copernicus GLO-30), channel geometry (HydroRIVERS), dam specifications (CWC/WRD), hydrological forcing (NWIC/WRD bulletins), permanent water baseline (JRC GSW v1.4), satellite SAR (Sentinel-1 GRD), and downstream exposure (OSM/WorldPop) is documented in [UJJANI_SITE_DATA.md](UJJANI_SITE_DATA.md).

Historical flood events selected for future validation are documented in [UJJANI_EVENT_MANIFEST.md](UJJANI_EVENT_MANIFEST.md): primary October 2020 Bhima Flood (~250,000 cusecs peak) and secondary August 2019 Krishna-Bhima Flood, with matched Sentinel-1 GRD scene pairs on compatible orbit geometry.

The strict 16-item readiness assessment in [UJJANI_MODEL_READINESS.md](UJJANI_MODEL_READINESS.md) yields verdict `NOT_READY_FOR_SITE_RUN` due to 3 BLOCKED items: sub-surface channel bathymetry, continuous upstream forcing telemetry, and downstream rating curve. Any simulation using current terrain-only channel approximation MUST be labelled `APPROXIMATE DEMONSTRATION — NOT VALIDATED SITE RUN`.

# Data manifest — phase 1, 2026-09-12

## Phase 3C export/data constraints

Exports consume only saved normalized numerical results and derived products; they do not reinterpret the raw Ujjani gate CSVs as complete hydraulic forcing. A result must carry an exportable CRS. Cell-centre vector coordinates are written in the saved result CRS and KML is transformed to WGS84 with `always_xy`; CSV depth states preserve `WET`, `DRY` and `NODATA`. GeoTIFF uses an explicit `-9999` nodata value and metres for depth. Shapefile field-name shortening is documented in `fields.txt` inside each archive.

No verified population, building, roads, farmland or critical-facility dataset was added. Consequently, ensemble settlement exposure and response priorities remain unavailable rather than inferred from missing data.

## Actual source retrieval

Source: [NWIC Ujjani catalogue](https://www.nwdp.nwic.gov.in/dataset/reservoir_discharge_ujjani_dam_1_maharashtra_telemetry_hourly), agency Maharashtra SW. CKAN API metadata is saved in `evidence/nwic-catalogue.json`. Retrieval responses, SHA-256 values and byte counts are in `evidence/source-audit.json`; per-gate statistics are in `evidence/hydrology-audit.json`.

| Original resource | Download | Actual rows | Actual source-local coverage (timezone unknown) | Non-hourly intervals | Largest gap |
| --- | --- | ---: | --- | ---: | ---: |
| 2021–2025 label, `bb63b1bb-76df-4bbe-8cb9-60313254ccb3` | HTTP 200 CSV, 978,304 bytes | 4,026 | 2023-10-23 03:00 to 2025-10-23 05:00 | 804 | 2,832 hours |
| 2026–2030 label, `696d5dc7-b8e2-4d3b-80d2-68512962ba35` | HTTP 200 CSV | 1,411 | 2026-03-25 16:00 to 2026-09-10 23:00 | 188 | 986 hours |

Original files are preserved outside Git at `data/raw/<resource-id>.csv`. They are agency observations with **unresolved interpretation**, not synthetic data. Their timestamps have no supplied UTC offset. No timezone was invented. No interpolation, zero filling or total gate sum was performed. No duplicate timestamps or out-of-order records were found in either resource. Quality flag columns were absent; that is not proof of data quality.

Both CSVs identify station `Ujjani Dam_1`, agency `Maharashtra SW`, district Solapur, and report longitude 75.12002000 / latitude 18.07402000. These are **source-reported station coordinates**, not an independently surveyed dam polygon or downstream study boundary. The CSV does not establish coordinate datum, surveyed accuracy, channel geometry or a computation CRS.

Critical conflicts:

- Catalogue description says m³/s; actual gate headers say **cusec**. Use the actual file's units with explicit conversion only after measurement meaning is verified.
- Resource display names say daily reservoir water level despite discharge filenames and gate-discharge headers.
- The file contains 50 generic gate columns. Nonzero series do not establish how many physical gates/pathways exist. Columns 45–50 are mostly or entirely missing; other columns also contain missing values. Missing gates must not be summed as zero.
- Gate-to-river/canal/other-outlet mapping, total release completeness, timezone and flags need agency or dam-owner documentation.
- The advertised year ranges do not describe complete downloaded coverage. Long gaps make a blanket multi-year replay unusable without selecting an audited event window.

The catalogue licence reads `Other (Open)`. Retain this exact attribution; specific reuse terms are unresolved. No raw records were placed in redistributable examples. Acquisition interval comes from individual rows; retrieval UTC time/checksum are recorded in evidence. No vertical reference applies to discharge values themselves, but level/terrain inputs still need one.

## Repeat the audit

Fetch the public CKAN package metadata using the API URL in `scripts/audit_sources.py` / saved manifest, then run:

```powershell
py -3.12 scripts\audit_sources.py
py -3.12 scripts\audit_hydrology.py
```

The fetcher limits responses to 25 MB, records HTTP failures, and does not submit credentials. It stores raw CSVs outside Git. The generic app importer can map one verified discharge series using explicit column names, `%d-%m-%Y %H:%M` timestamp format, confirmed timezone and `cusec` units. A verified total-outflow derivation still needs the physical gate/pathway inventory; a single gate must not be relabelled total river outflow.

## Exact missing inputs

| Input | Required evidence | Current state |
| --- | --- | --- |
| Hydraulic terrain GeoTIFF | Appropriate coverage, source resolution, licence, CRS, vertical reference, nodata review | Missing |
| Bhima channel bed / cross-sections | Survey or reusable documented bathymetry with elevation reference | Missing |
| Domain and structures | Reviewed downstream endpoint, tributaries, bridges/weirs and boundary locations | Missing; no endpoint chosen |
| Complete river outflow CSV | Gate/pathway inventory, actual aggregate Q(t), confirmed timezone, gaps/flags for selected event | Raw gate records retrieved; usable forcing blocked |
| Initial river / downstream / tributary conditions | Time-aligned, referenced levels/discharge or explicit justified assumptions | Missing |
| Roughness | Spatially referenced values or documented assumption | Missing |
| Breach inputs | Verified dam component, method applicability, level-storage curve, starting level/storage, inflow and all release pathways | Missing |
| Population/assets/facilities/roads | Verified geometry, year, coverage, units, licence | Missing; optional for basic hydraulics |
| Independent event evidence | Matching stage/discharge or acquisition-time flood observations | Missing |

Tests create independent synthetic laboratory fixtures in temporary directories. They are not added to the Ujjani project. Hydraulic terrain and drainage-conditioned rasters are distinguished by contract; the latter cannot pass the hydraulic readiness check. Reprojection/resampling is not implemented or claimed to improve source accuracy.
