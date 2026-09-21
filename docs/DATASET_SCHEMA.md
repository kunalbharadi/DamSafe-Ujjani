# Dataset and Scientific Input Contract

## Universal metadata

Every source record needs: human name, kind, source agency, original source URL, licence, acquisition date or explicit missing-date note, units, CRS where spatial, vertical reference where elevation/stage is used, status (`observed`, `derived`, `assumed`), `synthetic` boolean, processing history, original filename, byte size, SHA-256 and ingestion time. Do not use an empty value to mean zero.

Quality flags should use source flags where defined, plus project review states such as `ACCEPTED`, `SUSPECT`, `REJECTED`, `MISSING`, `ASSUMED`, and `OUTSIDE_COVERAGE`. Keep the original flag and its definition.

## Ujjani–Bhima input inventory

| Dataset | Required? | Contract | Current verified status |
|---|---|---|---|
| Terrain DEM | Required | GeoTIFF, explicit CRS/nodata/resolution/vertical reference, domain coverage | PARTIAL: repository-local Copernicus-named tiles and terrain evidence exist; licence/source lineage must be checked before redistribution |
| River bathymetry/cross-sections | Required for scientific site model | GeoJSON/GPKG points/lines/polygons with surveyed elevations and datum | BLOCKED: absent |
| Dam/structure geometry | Required | sourced crest/spillway/gate/component geometry, elevations/datum | PARTIAL: coded reference values; primary-source verification remains a team responsibility |
| Historical release/discharge | Required for historical mode | CSV schema below; observed station identity and quality | BLOCKED for a qualified assessment event |
| Reservoir level–storage | Required for computed breach | monotonic level/storage table with datum/source | BLOCKED as qualified operational curve; scenario code supports a curve |
| Initial level/storage | Required per breach | timestamped observation or explicit assumption | DATA REQUIRED per event |
| Downstream/initial/tributary boundaries | Required | timestamped flow/stage with location/datum/quality | BLOCKED |
| Roughness/land cover | Required for calibrated site model | raster/vector categories and documented Manning mapping | BLOCKED; uniform/assumed roughness is demonstration-only |
| River structures | Required where hydraulically material | bridges/weirs/embankments with geometry/coefficients | BLOCKED |
| Sentinel-1 pre/event scenes | Required for satellite assessment | metadata and masks below | PARTIAL: retrieval/processing definitions exist; live/authentic local execution not established for final assessment |
| Gauge observations | Required for hydrograph validation | station, datum, stage/discharge, timestamps, flags | BLOCKED |
| Settlements/buildings/roads/facilities | Required for impact/HADR | qualified vector layers with stable IDs and licence | BLOCKED |
| Population | Optional product dependency | dated gridded/vector counts and method | BLOCKED |
| Agriculture/land cover | Optional impact dependency | classified raster/vector and season/date | BLOCKED |
| Depth-damage/asset values | Optional loss dependency | accepted local functions/currency/base year | DEFERRED |

## Schemas

### DEM

GeoTIFF, one elevation band unless bands are explicitly mapped; numeric metres; explicit EPSG/WKT, transform, nodata, pixel size, bounds, acquisition/product date, vertical datum/geoid, source product/tile ID and processing history. Hydraulic DEM use must document whether vegetation/buildings and riverbed have been corrected. Mosaicking/reprojection/resampling records include tool, version and method.

### Hydrological CSV

```csv
timestamp,station_id,discharge_m3_s,water_level_m,flag
2026-01-01T00:00:00+05:30,FICTIONAL_STATION,125.0,,OK
```

Declare `timestamp_column`, format if non-ISO, source timezone, value/station/flag columns, sampling interval, accepted flags and measurement type (`river_outflow`, `canal_release`, `reservoir_level`, `unknown`). Never mix stage and discharge in one value column without an explicit variable field.

### Level–storage and release hydrograph

```csv
level_m,storage_m3,vertical_datum,quality_flag
450.0,1000000.0,EXAMPLE_DATUM,ASSUMED
```

Levels and storage must be strictly increasing with at least two rows and non-negative storage. A release hydrograph uses `elapsed_s,discharge_m3_s` or aware `timestamp,discharge_m3_s`, plus source/method and quality. Do not label empirically generated breach discharge as observed.

### River geometry and structures

GeoJSON/GPKG geometry must use a declared CRS. Features require stable IDs, role/type, source, survey date, and quality. Cross-sections need station/chainage, point order, elevation and vertical datum. Structures need type, crest/deck/invert elevations, dimensions, coefficients and source.

```json
{"type":"Feature","properties":{"feature_id":"fictional-xs-01","feature_type":"cross_section","chainage_m":1000,"vertical_datum":"EXAMPLE_DATUM","quality_flag":"ASSUMED"},"geometry":{"type":"LineString","coordinates":[[75.0,18.0],[75.001,18.001]]}}
```

### Exposure layers

Land cover needs class code/name, classification system, date, resolution and licence. Settlements/buildings/roads/facilities need stable ID, feature type, name if published, source date, geometry quality and licence. Population needs count/value, reference year, enumeration unit and allocation method. Null counts remain null.

### Sentinel-1 observation

Required metadata: collection and exact scene IDs, acquisition UTC, pre/event role, platform, IW mode, GRD product, VV/VH polarization used, pass direction, relative orbit, footprint/coverage, pixel CRS/transform/resolution, calibration and terrain-correction method, dB versus linear handling, speckle method, change threshold/method, permanent-water mask, slope/shadow/unreliable mask, valid-pixel count, processing time, software/version, source URL, licence and file checksum. A discovered scene without a generated/verified flood mask is `SCENE_DISCOVERED`, not validation evidence.

## Null and readiness rules

Blank, NaN, nodata, outside coverage and rejected observations never become zero. Zero is valid only when the source defines it. Readiness checks verify file/kind, checksum, parseability, CRS/datum, units, temporal coverage, spatial overlap, monotonic time, duplicate timestamps, station identity, flags, synthetic/project separation, scenario ownership and historical-event compatibility.

## Repository data and sharing

Tracked, small, redistributable evidence includes configuration JSON, test fixtures embedded by tests, audit JSON, manifests, logs and small CSV evidence under `docs/evidence/`. These remain labelled benchmark, synthetic, assumed or derived as applicable.

Large raw rasters, native solver workspaces, downloaded satellite imagery, database files, exports and generated frontend bundles belong under ignored `data/`, `.local/`, `scratch/` or external controlled storage. Share them through a source manifest containing URL, licence, checksum, size, CRS/datum and retrieval instructions. Never commit credentials, restricted WRD/CWC records, or data whose redistribution licence is unclear. `DATA_MANIFEST.md` and `DATASETS.md` contain earlier inventory details; where they conflict, this contract and verified code behavior prevail.
