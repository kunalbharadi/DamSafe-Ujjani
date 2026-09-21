# DamSafe UI and UX Guide

## Navigation and journey

The authoritative hierarchy is: **Dashboard, Study Area, Data Setup, Scenario Builder, Simulation, Results, Validation, Impact & HADR, Reports & Export**. The React root is `frontend/src/main.tsx`; pages live in `frontend/src/pages/`, shared components in `frontend/src/components/`.

| Page | Purpose | Current status | Rule |
|---|---|---|---|
| Dashboard | project mission control, readiness and latest retained output | IMPLEMENTED | Metrics must derive from selected saved result or show unavailable |
| Study Area | Ujjani/Bhima location, reach/domain and sourced metadata | PARTIAL | Domain/reference map is not proof of simulated extent |
| Data Setup | inventory, provenance, upload and readiness | IMPLEMENTED | Each category shows available/assumption/data required/blocked |
| Scenario Builder | immutable prescribed-release or computed-breach scenario | PARTIAL | River blockage remains NOT IMPLEMENTED; full breach generation is not API-integrated |
| Simulation | engines, configuration, progress, cancel and history | IMPLEMENTED | DualSPHysics is near-field/laboratory, not full reach |
| Results | 2D frames, native regional 3D mesh, SPH particles, comparison | PARTIAL | native face polygons where available; surrounding Cesium terrain absent |
| Validation | Earth Engine/import status, satellite/gauge evidence | PARTIAL/BLOCKED scientifically | No score without qualified matching data |
| Impact & HADR | supported exposure and response data | BLOCKED scientifically | Do not show fixed backend demo values as observed impact |
| Reports & Export | six exports and actual-data report view | IMPLEMENTED/PARTIAL | State that vectors are cell points; report limitations |

Old module-oriented destinations such as separate Data Library, Readiness, Ensembles, Observations, Exposure and Exports are merged into the workflow above. Ensemble capability remains backend/API functionality and should appear only where users can understand scenario-frequency semantics.

## Screen specifications

- **Dashboard:** DamSafe purpose, selected Ujjani project, New Simulation/Open Latest Results, readiness/run/result/validation cards, geographic preview and workflow steps.
- **Data readiness:** six data categories, status/source/findings, audit action, bounded upload with contract help.
- **Scenario builder:** distinct historical release and hypothetical breach modes; only implemented fields; source/assumption classification; immutable-save explanation.
- **Simulation:** D-Flow FM regional and DualSPHysics near-field cards; availability, exact case kind, state/progress, cancel, previous runs and bounded error text.
- **2D map:** MapLibre context, depth/velocity layers supported by API, play/pause/step/time, units, provenance and separate WET/DRY/NODATA. Render cell centres honestly until polygon geometry exists.
- **3D:** optional. SPH uses real saved `THREE.Points`; classification and derived variables are labelled. Regional view must state it extrudes/displays 2D output. Hide “terrain” claims until an authoritative terrain source is rendered.
- **Comparison:** allow only compatible saved runs; display incompatibility rather than stretching grids.
- **Impact:** show real overlay values only with dataset/geometry provenance. Otherwise show DATA REQUIRED.
- **Satellite:** visually distinguish historical event and latest available; show scene/provenance/quality/readiness; metrics only after compatibility checks.
- **Export/report:** cards for GeoTIFF, Shapefile, KML, GeoJSON, CSV, HTML; selected run, generation state, provenance and limitations.

## Visual system

| Token | HEX | Use |
|---|---|---|
| Brand orange | `#F97316` | primary actions/identity |
| Dark orange | `#EA580C` | hover/focus accents |
| Orange tint | `#FFF7ED` | selected/attention backgrounds |
| Readiness green | `#16A34A` | verified available/pass only |
| Hydrology blue | `#2563EB` | water/data controls |
| Water blue | `#38BDF8` | shallow-water visualization |
| Background | `#F8FAFC` | app canvas |
| Surface | `#FFFFFF` | panels |
| Primary text | `#172033` | headings/body |
| Secondary text | `#64748B` | supporting text |
| Border | `#E2E8F0` | boundaries |

Orange identifies actions, blue identifies hydrology, green means verified readiness. Hazard scales retain meaningful blue/yellow/orange/red ramps. Every state has text/icon, not colour alone. Text/background pairs must meet WCAG AA; visible keyboard focus is mandatory.

Use the system sans-serif stack in `style.css`, 16 px readable body text, compact 8 px spacing increments, few purposeful cards, one primary action per page, responsive tables, explicit labels and units. Buttons need loading/disabled reasons. Forms keep error text next to the field. Maps always show legend, units, current time, layer source and nodata semantics.

## Application states

- **Loading:** preserve layout and announce progress; disable repeat submission.
- **Empty:** explain what input/action creates content.
- **Error:** show bounded actionable text, preserve previous valid state.
- **Blocked/Data Required:** identify exact external input; never replace it with zero.
- **Unavailable:** explain engine/service requirement.
- **Synthetic/imported/cached:** permanent visible badge and provenance.

Desktop targets are 1366×768 and 1920×1080. At narrower widths, sidebar collapses, grids stack, tables scroll and map controls remain reachable. Mobile is secondary but cannot hide status/limitations.

## Acceptance checklist

- Nine destinations render useful content and have a working primary action or a clear blocked state.
- No sample metric appears without source run/dataset classification.
- No fixed exposure value, invented population/loss/route or fabricated validation score appears.
- Historical/latest modes and solver/site/laboratory classifications remain visible.
- Keyboard navigation, focus, labels, contrast, zoom and screen-reader status work.
- Timeline/frame label matches the values currently rendered.
- Map legends include units and distinguish wet/dry/nodata.
- Export controls call implemented APIs and report errors.
- Existing local screenshots are `docs/evidence/setup-desktop.png` and `setup-mobile.png`; they are historical evidence and may not reflect the current rebuilt pages.
