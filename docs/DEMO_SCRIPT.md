# DamSafe local demonstration

Start with `./scripts/start.ps1 -Preview`, then open `http://127.0.0.1:8000`. The launcher creates a missing local .env; [environment setup](ENVIRONMENT.md) explains credentials. Retained data/results must be present locally; a fresh source checkout does not contain large engine outputs.

1. **Dashboard:** select the Ujjani project in the top bar. Show actual first-saved-frame depth and wet area, readiness gaps and NOT VALIDATED status. Initial water is included in wet area.
2. **Study Area / Data Setup:** inspect source and dataset readiness. Explain missing surveyed channel data, forcing/boundary records and datum qualification.
3. **Scenario Builder:** inspect/save an immutable release or hypothetical-breach scenario. Custom site execution remains blocked because full worker input binding is incomplete.
4. **Simulation:** use the project selector to open the separate laboratory workspace. With pinned engines installed, submit an official example. If reused from cache, explicitly call it cached; QUEUED/RUNNING is not proof of success.
5. **Results, 2D:** return to Ujjani and select a retained successful run. Show numerical depth/velocity, native mesh polygons, frame slider and wet/unknown area. This is an approximate saved numerical demonstration.
6. **Results, 3D River Mesh:** rotate and zoom the native face bed/water surface. Change vertical exaggeration. Surrounding photorealistic terrain is not present.
7. **Results, 3D SPH Near-Field:** play or seek to frame 100. Show actual particle count, speed and time. These are local laboratory coordinates, not a georeferenced Ujjani SPH simulation.
8. **Compare:** select compatible outputs in the same project. Show agreement metrics and provenance. Incompatible pairs stay rejected; no inter-model agreement is labelled accuracy.
9. **Validation:** distinguish historical from latest-available observation mode. Explain Earth Engine access and full observation assessment are unverified/incomplete. Do not show an unrelated image as breach validation.
10. **Impact & HADR:** show explicit missing asset/population/loss evidence. Do not invent exposed settlements or evacuation routes.
11. **Reports & Export:** generate KML, Shapefile ZIP, GeoJSON, GeoTIFF, CSV or HTML. Explain vector exports use cell points and retain run provenance.

Verification: `cd frontend; node tests/review-local.mjs` starts an isolated API, exercises all pages and real retained result playback/exports, and stores screenshots in `.local/ui-review/`. It does not submit new numerical runs.

Use [FINAL_READINESS.md](FINAL_READINESS.md) for the exact scientific claim boundaries. Neither a completed demo nor a passing application build establishes full PS compliance.
