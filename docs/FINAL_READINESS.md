# Final readiness — 2026-09-21

This is a demonstrable local application with genuine retained numerical output, not a completed or independently validated Ujjani forecasting system. See [project status](PROJECT_STATUS.md) for engineering gaps and [environment setup](ENVIRONMENT.md) for credentials.

| Deliverable | Status | Evidence and limit |
|---|---|---|
| Application works | PASS | Production build, nine-page live browser review, SQLite persistence and API tests |
| D-Flow FM actually ran | PASS | Retained phase2 evidence plus direct terrain/release and breach native smoke tests on this machine |
| DualSPHysics actually ran | PASS | Retained phase2 particles and execution evidence; current browser replays saved output |
| Ujjani inputs verified | PARTIAL | Terrain/source manifests exist; bathymetry, forcing, boundaries, datum and roughness require qualification |
| Ujjani simulation ran | PARTIAL | Retained approximate numerical case; direct bounded terrain/breach smoke execution; arbitrary saved site-scenario submission remains blocked |
| Both models compared on compatible site data | BLOCKED | Laboratory comparison capability is not a two-engine Ujjani assessment |
| Historical event assessed | BLOCKED | No qualified acquisition-time simulation/reference pair or independent gauge record |
| Google Earth Engine executed | BLOCKED | OAuth/service-account wiring tested with mocks only; authorized live account required |
| Exports verified | PASS | Six formats generated from retained output and checked by API/browser tests; vector export semantics remain cell points |
| Loss estimation supported | BLOCKED | Asset inventories, valuations and damage functions absent |
| Domain expert review obtained | BLOCKED | No review evidence supplied |
| Natural blockage/debris/erosion/rainfall-runoff/full-domain 3D SPH | DEFERRED | Not implemented and tested |

## What the demo shows

The dashboard reads actual first-frame depth and wet area. The 2D map displays native computational polygons where available, fixed numeric depth/velocity legends and bounded playback. Regional 3D displays saved native face bed/water surfaces. SPH displays actual laboratory particles with orbit, zoom and frame playback. Source coordinates, result identity, classification and limitations remain visible.

A regional mesh display is not photorealistic surrounding terrain or a 3D hydraulic solver. A laboratory particle run has no Ujjani geographic coordinates. Wet area can include initial river water and is not automatically newly flooded land.

## Testing limits

Two legacy site-lifecycle tests are expected failures because arbitrary saved scenario parameters are not bound into the site worker. They do not count as passes. Separate short native D-Flow terrain/release and breach tests verify actual execution when the installed image and local DEM files are available. Skips on another machine mean those scientific checks were not executed there.

Earth Engine initialization tests use mocked provider calls and do not establish live access. The live query implementation currently discovers scenes; full near-real-time classification and historical assessment remain incomplete. Filename-only satellite authenticity was removed.

## Handover

Start locally with `./scripts/start.ps1 -Preview`; open `http://127.0.0.1:8000`. Use the project selector for the separate laboratory workspace. Native engine execution requires the pinned Docker images and source checkouts. Large retained datasets and result files are not committed; a fresh checkout requires the documented data/evidence setup.

No public deployment, independent Ujjani validation or full PS compliance is claimed. Sponsor clarification is needed if the expected comparison requires both engines across the same regional site domain instead of a compatible local comparison.
