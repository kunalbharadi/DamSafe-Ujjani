# Model and ingestion contracts — version 1

The executable schema is `backend/damsafe/contracts.py`, also exposed in FastAPI OpenAPI. Extra fields, nonfinite numbers and naive scenario timestamps are rejected. Python frozen models alone are not the persistence guarantee: snapshots are serialized, hashed, and the database rejects dataset/scenario updates and deletes. Changed inputs require new versions/snapshots.

## Source upload

`POST /api/projects/{id}/datasets?filename=flow.csv&metadata_json=<URL-encoded JSON>` takes the file as the raw request body (`application/octet-stream`). The server streams at most 64 MiB; it checks actual received bytes even without Content-Length. The supplied filename is never used for an object path. Project/UUID keys are generated server-side and restricted by the storage interface. A successful import stores original bytes, SHA-256, byte count, server retrieval timestamp, metadata, inspection and version.

Synthetic example metadata (must only go into a synthetic project):

```json
{
  "name": "Laboratory discharge fixture",
  "kind": "hydrology",
  "provenance": {
    "source_url": "fixture://software-tests", "agency": "Software tests",
    "licence": "Synthetic test fixture", "acquisition_date": "2025-01-01",
    "units": "m3/s", "status": "assumed", "synthetic": true
  },
  "hydro": {
    "station_id": "fixture", "measurement": "river_outflow",
    "identity_reference": "fixture://software-tests", "interval_seconds": 3600
  }
}
```

CSV columns default to `timestamp,station_id,discharge,flag`. ISO timestamps with UTC offsets are preferred. Naive values require an explicitly supplied IANA `source_timezone`; ambiguous local times are rejected. A custom `timestamp_format` is supported. `m3/s` and `cusec` are the only accepted discharge units; one cubic foot is converted using 0.028316846592 m³. Summary values use m³/s; raw bytes remain unchanged. Missing values, duplicates, cadence gaps, unknown measurement pathway, absent station evidence and unaccepted flags create blocking findings. Negative/nonfinite discharge is rejected; reverse-flow boundaries would need a separate signed contract in phase 2.

Terrain: `kind=terrain`, `.tif`/`.tiff`, single-band GTiff, units `m`, declared CRS agreeing with embedded CRS, provenance vertical reference, `terrain_purpose=hydraulic|drainage`. Inspection reads fixed 512-cell windows, with a 100-million-cell limit. It reports source resolution and nodata without changing elevations. Unknown datum and nodata prevent readiness.

Vectors: `kind=river|structures|exposure|roughness`, `.geojson`/`.gpkg`, declared CRS, valid nonempty geometry, at most 200,000 features. Multi-layer GeoPackage requires a selected layer. GeoJSON follows its WGS84 longitude/latitude convention. Source extents are transformed to WGS84 for comparison, not treated as projected hydraulic coordinates. A centreline alone cannot establish adequate channel bed geometry; a mandatory phase-2 geometry review prevents it being declared sufficient.

## Scenario snapshots

`POST /api/projects/{id}/scenarios` saves name, forcing, referenced immutable dataset IDs, offset-aware start/end time, positive model time step, output interval, wet/dry threshold and arrival threshold. Output interval cannot be shorter than time step; arrival threshold cannot be below the wet threshold. Missing essential setup may be saved for review but cannot execute.

Referenced initial river state, downstream boundary, tributary inflows, structure treatment and roughness need description, source references and observed/derived/assumed status. Initial state/downstream level references must agree with the project elevation reference. Project computation coordinates remain unset until verified domain bounds support an appropriate metre-based projected CRS. Bounds must lie inside that CRS's area of use. Source terrain must cover the domain; vectors must intersect it. No silent datum conversion or exploratory override is currently supported: unknown references stay blocked.

- `forcing.mode=prescribed_release`: `historical` boolean and a selected `hydrograph_dataset_id`. Historical mode needs observed or traceably derived actual forcing and complete time coverage. An exploratory supplied hydrograph is not a computed breach.
- `forcing.mode=computed_breach`: initial level/storage, strictly increasing level–storage pairs with nonnegative volumes, reservoir inflow, all other release pathways, dam component, method applicability evidence and parameters. An independently prescribed hydrograph field is rejected. Physical interpolation/balance/method execution is deliberately blocked until phase 2; scalar percentage-failure shortcuts do not exist.

Snapshots contain the complete project configuration, scenario, source metadata, input inspection and file hashes. API reads cannot mutate earlier versions. Dataset selection across projects is rejected. The SHA-256 covers canonical sorted JSON of the complete snapshot, not just a display name.

## Separate status dimensions

| Dimension | Values / meaning |
| --- | --- |
| Execution state | QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED; applies to the actual job |
| Input mode | OBSERVED, MIXED_ASSUMPTIONS, SYNTHETIC; calculated from explicit metadata/assumptions, not user-issued certification |
| Evidence status | UNASSESSED, BENCHMARK_CHECKED, HISTORICAL_EVENT_ASSESSED; current snapshots always UNASSESSED |
| Execution origin | LOCAL or IMPORTED; imported numerical results require engine/version/source provenance |

`RunManifest` defines scenario hash, engine identity/version, executable hash, execution origin and source references. Phase 2 added a separate immutable `runs` table and `POST/GET /api/projects/{id}/runs` plus cancellation. Currently executable requests are restricted to official example inputs in synthetic projects, with a hash-pinned local engine image. An unavailable image returns 503; a site scenario returns 422 with readiness findings because no verified site mesh/forcing is available. The SQL queues execute readiness audits and bounded numerical jobs separately. A successful audit does not mean input readiness, and a successful numerical process does not mean validation. Cancellation cannot be overwritten by late completion. Stale audit and numerical leases become FAILED, never SUCCEEDED. See [phase 2 evidence](PHASE2_EVIDENCE.md) for exact engine/run status.

The phase 2 normalization schema is face/column-centred NetCDF with `time`, `x`, `y`, `cell_area`, `bed`, `h`, `eta`, `u`, `v`, `valid`, `wet` and embedded provenance. D-Flow mapping requires matching 2D face/time dimensions and explicit projected CRS/datum. Missing native fields remain unavailable. SPH 2D x/z particles are converted to per-unit-breadth volume-equivalent column depth using native particle mass/density and volume-weighted horizontal velocity; vertical impact/splash dynamics are flagged outside the shallow-water comparison. This normalized schema is not a Ujjani map until site geometry/forcing are verified.

## Phase 3A saved-result contract

See [Phase 3A report](PHASE3A_REPORT.md) for endpoint parameters, response states and resource bounds. A numerical run is successful only after normalized output validation and background product generation both complete. Each result read checks project/run ownership, successful state, exact configuration identity for cache aliases and saved-output SHA-256. Configuration identity covers the immutable request, pinned engine image/source commit and official input hashes; changing the request creates a new identity. A valid cached result gets its own run ID and explicit source-run provenance. Site scenario IDs remain required and distinct, but site execution remains blocked by readiness.

The `products.nc` derived schema contains per-cell maximum depth, maximum velocity magnitude, flood duration, arrival elapsed seconds, `cell_state`, `valid_frame_count`, and per-frame known flooded and unknown areas. `cell_state` values are `NODATA=0`, `NOT_REACHED=1`, `REACHED=2`. Instantaneous `DRY` is a separate valid saved-depth state. Arrival is the first saved frame reaching the configured threshold; duration is a left-held saved-frame estimate and is unavailable with incomplete frame coverage. No external permanent-water baseline is accepted without a verified geospatial mask. All site products remain unavailable until genuine site outputs exist.
