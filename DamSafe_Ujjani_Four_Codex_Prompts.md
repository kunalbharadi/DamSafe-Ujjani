# DamSafe: Ujjani–Bhima workflow, PRD review, and four Codex build prompts

Prepared for SIH PS 26161. This is an implementation brief, not evidence that a solver, dataset, or application has already been validated.

**Use:** Put this file in the intended project repository. Paste each of the four numbered prompt blocks into Codex, sequentially, in that same repository. Keep the generated project documents between stages. A stage can require a long coding session and corrections; four messages cannot guarantee scientific validity or remove unavailable-data and installation blockers.

## Scope and working model

Use Ujjani Dam and a bounded downstream reach of the Bhima River as the only demonstration site. Determine the downstream endpoint after inspecting terrain, tributaries, hydraulic structures, and observation stations. Do not promise to reach Pandharpur before this inspection. Keep datasets and site configuration external to the application code so the framework remains reusable.

There are two separate simulation modes:

1. **Historical release replay:** import an actual discharge-versus-time series, combine it with the river's initial state and relevant tributary/downstream conditions, then simulate a recorded event. Compare matching observations where available.
2. **Hypothetical failure scenario:** use documented reservoir geometry or level–storage information and an explicitly assumed breach evolution to generate an outflow hydrograph, then route it downstream. The failure assumption is not a forecast of Ujjani failing. A user-supplied hypothetical hydrograph can support exploratory routing but is not itself a calculated breach model.

A hydrograph Q(t) specifies discharge in cubic metres per second through time. The reservoir routing accounts for incoming water, all outgoing pathways, and remaining storage. Prescribed release mode and computed breach mode must have separate input contracts: do not independently force a discharge and calculate a second release from the same water volume.

Use **Delft3D Flexible Mesh / D-Flow FM** as the proposed primary 2D river/floodplain engine. Use **DualSPHysics** for a small, physically compatible local comparison case. Start comparison with a shared benchmark; a Ujjani local comparison remains a separate deliverable. Full-domain SPH is not required by this plan, and this interpretation of the PS should be checked with the problem owner if the expected spatial comparison scope is unclear.

Both solvers produce numerical results. Postprocessing derives flood extent, depth, velocity, arrival time, duration, and exposure. The browser displays those stored outputs; it does not invent water movement. A separate Google Earth Engine path extracts timestamped observed water/flood masks. Only a matching historical simulation can be assessed against that observation.

## Comparison with the uploaded PRD

The supplied `Pasted markdown(6).md` is a PRD, not implementation evidence. Its section 35 already proposes a single-site MVP; we are specializing and correcting that scope, not replacing an existing implemented model.

| PRD reference | Issue | Correction for this build |
| --- | --- | --- |
| Section 13, partial-failure scenario | Calls partial failure controlled release | Keep a failure scenario separate from an operational release scenario |
| Section 13, complete-failure scenario | Percentage failure implies maximum release without a physical definition | Use documented geometry, reservoir state, and time-dependent assumptions; do not infer a discharge from a percentage label |
| Sections 12 and 32 | River width/centreline and a few scalar fields are insufficient contracts | Add channel geometry, level–storage relation where needed, initial states, tributary inputs, downstream boundary, vertical datum, and time series |
| Section 11 | Blanket sink filling is treated as simulation-ready terrain | Preserve physical depressions/storage and barriers; keep drainage-conditioned terrain separate from hydraulic terrain |
| Sections 14–16 | Does not define a common comparison domain or common observables | Define equivalent forcing, common gauges, time alignment, masks, and SPH-to-depth-averaged comparison |
| Section 16 | Model differences are described as accuracy | Call them inter-model agreement; assess accuracy only against suitable independent reference evidence |
| Sections 20–21 and 43 | Satellite validation is presented as following any scenario | Assess a historical event at satellite acquisition time; hypothetical failure maps have no matching observed failure by default |
| Section 19 | Depth-only categories called risk | Call these depth/hazard classes; broader hazard considers velocity/duration and risk also requires exposure/vulnerability and, where relevant, likelihood |
| Sections 18 and 44 | Exposure is the main impact output | Keep exposure distinct from economic loss; damage estimates require asset values and justified vulnerability relationships |
| Section 32 | A single arrival_time per result | Store arrival-time maps or per-location series, a stated threshold, and explicit not-reached/no-data values |
| Sections 34 and 48 | Example metrics and relaxed comparison completion language can hide unfinished physics | No sample numbers on real cases; require actual runs or explicitly attributed imported results; imported results do not prove automatic solver integration |
| Sections 35 and 48 | 3D is treated as core completion | Prioritize numerical engines, comparison, GIS outputs, and validation; terrain rendering is optional polish |
| Sections 36–37 | AI suggestions and broad platform features imply innovation | Defer LLM parameter suggestions. Focus on input provenance, uncertainty, and explainable evidence |

The first release covers controlled/prescribed releases and hypothetical breach scenarios. Natural blockage failure, erosion/debris transport, rainfall-runoff generation, and full 3D regional CFD are explicitly deferred. This is a scoped demonstrator, not a claim to cover every scenario in the PS.

## Prompt 1 — Foundation, site audit, contracts, and real data ingestion

```text
Build phase 1 of DamSafe for SIH PS 26161: a reproducible, one-site Ujjani–Bhima flood-modelling application. Execute the work in the current repository; do not stop at a proposed architecture.

First inspect AGENTS.md and other applicable instructions, repository status, current code, installed tooling, OS, Python/Node environments, and available CPU/RAM/GPU. Preserve user changes. Reuse working implementation and explain any necessary replacement. Do not modify unrelated repositories or deploy publicly. Read DamSafe_Ujjani_Four_Codex_Prompts.md and the uploaded PRD if present. This prompt's narrower scope and scientific corrections control the implementation plan.

Use React/TypeScript with MapLibre, FastAPI/Pydantic, PostgreSQL/PostGIS, a background-worker queue, and storage behind a local-filesystem/S3-compatible interface unless existing sound architecture gives a reason to retain equivalents. Use compatible dependency versions checked against official documentation; create lockfiles. Never store credentials or bulky solver outputs in Git.

Create a persistent project baseline: README.md, docs/PROJECT_STATE.md, docs/DATA_MANIFEST.md, docs/MODEL_CONTRACTS.md, docs/VALIDATION_PLAN.md, and docs/PS_COMPLIANCE.md. The compliance matrix must map each PS deliverable to code, evidence, and one of implemented/tested/blocked/deferred. Do not equate scaffolded with implemented.

Ujjani is selected, but the downstream domain and data are not yet validated. Inspect the official NWIC dataset:
https://www.nwdp.nwic.gov.in/dataset/reservoir_discharge_ujjani_dam_1_maharashtra_telemetry_hourly
Retrieve actual records if available and permitted. Validate the station identity and what the measurement represents, timestamps/timezone, units, flags, gaps, duplicates, and coverage. Catalogue presence does not prove complete usable data. Do not treat a canal-discharge or reservoir-level record as river outflow. Do not turn missing measurements into zero or silently interpolate across flood peaks. If retrieval fails, build the importer and record the exact missing file; continue independent work.

Build versioned imports for terrain GeoTIFF, hydrology CSV, and river/structure/exposure GeoJSON or GeoPackage. Record source URL/agency, licence, acquisition date, retrieval date, checksum, units, CRS, vertical reference, processing history, and observed/derived/assumed status. Use parameterized site configuration, with no invented Ujjani coordinates, bathymetry, storage curves, or village counts. A separate synthetic fixture is allowed for software tests and must never appear as real Ujjani data.

Implement data readiness with actionable missing requirements for each simulation mode. Check horizontal CRS, elevation datum compatibility, units, spatial extent, nodata, time overlap, and geometry. Unknown vertical references require resolution or explicitly recorded exploratory assumptions, not silent conversion. Choose projected computation coordinates from verified bounds; keep WGS84 for appropriate map exports. Keep hydraulic terrain separate from any sink-filled drainage analysis raster. Resampling cannot manufacture finer source accuracy.

Define immutable scenario snapshots and run manifests. Scenario modes: historical/prescribed release and computed hypothetical breach. Include initial reservoir state and level–storage relation for computed routing, documented breach-method applicability and parameters, river/structure geometry, roughness, initial river state, tributary inflows, downstream boundary, model time step and output times, wet/dry thresholds, arrival threshold, and source references. Missing optional impact layers must not prevent basic hydraulic execution; missing essential hydraulic inputs must not silently pass.

Define separate run execution states (QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED), input mode (OBSERVED, MIXED_ASSUMPTIONS, SYNTHETIC), and evidence status (UNASSESSED, BENCHMARK_CHECKED, HISTORICAL_EVENT_ASSESSED). State categories must not imply real-world certification. Imported results carry execution_origin=IMPORTED and producing-engine provenance.

Build project/scenario/dataset APIs, basic migrations, server-side upload limits and safe path handling, and a small setup/readiness UI. Add health checks and one-command documented local startup. Restrict a development demo to local access unless authentication is implemented; never trust arbitrary uploaded filenames or user-provided shell commands.

Probe availability and supported startup of D-Flow FM and DualSPHysics early, without pretending an adapter is a working engine. Record installation/build constraints, licences, and available official examples. Do all feasible installation checks permitted by the environment.

Verify with meaningful tests: CSV gaps/units/timezones, CRS/datum rejection, malformed/path-traversal uploads, immutable scenario snapshots, and persistence across restart. End with changed files, commands actually run, observed results, unresolved inputs, and next-stage readiness. Save exact status in PROJECT_STATE.md so later prompts can continue without guessing.
```

## Prompt 2 — Actual numerical engines, breach routing, and model comparison

```text
Continue DamSafe phase 2 in the same repository. Read applicable instructions, PROJECT_STATE.md, DATA_MANIFEST.md, MODEL_CONTRACTS.md, VALIDATION_PLAN.md, and PS_COMPLIANCE.md. Inspect the current implementation and preserve working phase-1 code. Fix phase-1 issues that block numerical execution. Execute implementation and verification, not merely documentation.

The objective is actual hydraulic computation. Integrate Delft3D Flexible Mesh / D-Flow FM for a bounded 2D Bhima river/floodplain domain and DualSPHysics for a manageable comparison domain. Check current official source/build/run documentation and pin engine provenance. Do not invent command-line switches or Python APIs. Official starting repositories:
https://github.com/Deltares/Delft3D
https://github.com/DualSPHysics/DualSPHysics

Implement adapters with explicit capability checks, input preparation, execution, progress/log capture, cancellation, failure reporting, and output normalization. Execute binaries using fixed argument arrays and permitted paths; do not interpolate user text into shell commands. Bound job resources. Missing engines must report unavailable; never fall back silently to mock, bathtub mapping, a radial buffer, or browser particle animation.

First run an official small example in each engine, retaining input files, engine identity/version, invocation, logs, runtime, and outputs. Then implement the site input-to-run path. Distinguish an official example, a shared synthetic benchmark, a site-specific exploratory run, and a historical-event assessment. Success in one is not evidence of success in the others.

Implement two scenario contracts. In prescribed-release mode, apply documented Q(t) at the chosen upstream boundary and include justified initial/downstream/tributary conditions. In computed-breach mode, implement or integrate a documented, tested reservoir-routing/breach-outflow method appropriate to the verified dam component and assumptions. Prefer validated existing components where possible. Document method validity and limits; do not apply an earthfill empirical method indiscriminately to another dam type. Reservoir balance must include inflow, all release pathways, and remaining storage; prevent double-counting the same outflow or producing more water than available. Validate the level–storage relationship and time/unit conversions. No percentage-breach-to-discharge shortcut and no claim that a partial failure is controlled release. If the physical inputs are absent, preserve this as blocked and support only separately labelled prescribed-hydrograph experiments.

Prepare a bounded site mesh with explicit bed elevations, meaningful hydraulic structures, roughness, and open/closed boundaries. Use documented numerics suitable for rapidly changing flow and wetting/drying. Preserve solver-native outputs, then normalize water depth h, water-surface elevation, horizontal velocity components, time, wet mask, CRS/datum, and grid/mesh metadata. Respect face/node staggering and velocity orientation. Missing fields are unavailable, not zero. Never infer velocity from a moving flood polygon.

Define a shared comparison case physically suitable for both formulations, starting with a simple benchmark and then a small Ujjani local domain when inputs permit. Keep geometry, initial volume/state, forcing, time origin, boundary conditions, output times, and common gauges comparable. Particle spacing and mesh cell size are different discretizations, not equal physical accuracy. Document how particle outputs are converted to surface/depth and comparable depth-averaged velocities; flag breaking-wave/local-impact zones outside shallow-water assumptions. A shared benchmark alone does not finish the requested site comparison.

Compute model-to-model depth time-series differences, peak/timing differences, extent agreement, and runtime with hardware/resolution metadata. Call these agreement metrics, never accuracy against truth. Do not automatically average incompatible models. Do not substitute SPH-to-Delft coupling for independent comparison. Two-way coupling and full-river SPH are deferred.

Implement diagnostic reporting: water balance including all boundaries and wetting/drying treatment; nonfinite/negative state detection; wet/dry consistency; and grid/time-step/particle-resolution sensitivity on small cases. Document numerical tolerances from scale and solver/reference guidance, not a marketing target.

Test a relevant analytical or published laboratory benchmark with independent reference data appropriate to each model. Save reference provenance and computed errors. Run at least one actual solver-backed smoke case per available engine. Test that an absent executable, corrupted output, cancelled run, or nonzero exit cannot become a successful result. Never mark an integration test passed merely because it was skipped.

If a solver installation or site-data requirement is genuinely blocked, finish all independent adapter/parser/diagnostic work and preserve truthful status. Imported authentic outputs can support later UI testing only with origin, parameters, engine version, and input hashes; they cannot satisfy automatic execution. End with an evidence table: engine installed, official example run, common benchmark, Ujjani run, Ujjani comparison, and outstanding blockers. Update persistent documents and compliance status.
```

## Prompt 3 — Working dashboard, exposure, scenario uncertainty, and GIS exports

```text
Continue DamSafe phase 3 in the same repository. Read applicable instructions and all phase status/contracts. Inspect actual files and run evidence. Repair blocking prior-stage integration defects where feasible. Do not label an unavailable solver or a failed site run as implemented merely to finish the UI.

Build a coherent user journey: Ujjani project overview, data-readiness review, scenario configuration, run/progress/cancel, numerical result exploration, scenario/model comparison, exposure analysis, and export. Integrate every control with the backend. Remove dead buttons and unsupported promises. Keep 2D MapLibre as the primary map; 3D terrain is optional after the required numerical and export paths work.

Use stored numerical outputs to animate flood depth and velocity over time. Playback between output frames must identify interpolation when used; exact metrics use actual saved outputs. Provide units, UTC/source-local time labels, simulation elapsed time, legends, study-domain boundary, nodata and wet/dry distinctions, and a fixed comparison colour scale. Avoid stretching different runs independently to look similar. Do not load entire multi-gigabyte arrays into the browser: implement spatial/time windows, raster tiles or appropriate mesh tiling, background postprocessing, and bounded memory reads.

Derived products: flooded area excluding the defined baseline/permanent reservoir water where appropriate; maximum depth; velocity magnitude; duration; per-cell/per-settlement arrival above a documented threshold; and location time-series charts. Store not-reached and outside-domain separately. Disclose output-time resolution limits on arrival estimates. A single overall arrival-time card must name its location. Respect terrain datum, masks, projection and metric area calculations. Do not calculate flood extent using disconnected terrain below an arbitrary water level.

Implement exposure overlays only for verified available layers: population grids, buildings, roads, farmland, and critical facilities. Respect whether population rasters encode counts or density and conserve counts during any resampling. State dataset year, coverage and aggregation assumptions. Count unique assets; clip flooded road lengths and handle boundaries consistently. Do not turn missing building data into zero buildings, or population exposure into predicted casualties. Depth/hazard categories must show the chosen method and thresholds; do not call depth-only classes full risk.

Economic damage is a separate optional capability requiring traceable asset values and applicable vulnerability functions. If those inputs are missing, show unavailable and record the loss-estimation gap in PS_COMPLIANCE.md. Do not invent rupee losses to complete a chart.

Build a small user-configured scenario ensemble with immutable input variants and real solver execution. Report extent intersection/union, depth/arrival ranges, and settlements exposed across the tested scenarios. Call unweighted counts scenario frequency, not real-world probability. Preserve no-flood outcomes when reporting conditional arrival-time ranges. Cache only identical model+input+configuration hashes and label cached results. Do not pretend interpolated outputs are new simulations.

The differentiators are input provenance and missing-data checks, physically meaningful model comparison, and response priorities that remain consistent across scenarios. Provide an explanation for each settlement priority using simulated arrival/hazard, available exposure, and scenario consistency. Defer automatic safe-route guarantees and emergency notifications.

Implement working exports: GeoTIFF with CRS/nodata/units; WGS84 KML; GeoJSON with documented coordinate convention; zipped Shapefile with .shp/.shx/.dbf/.prj and .cpg as appropriate; CSV location time series; and a concise report with maps, sources, assumptions, engine/run provenance, evidence status and limitations. Sanitize all export attributes and paths. Verify exports by reopening them with an independent reader and checking CRS, geometry, units, area, masks, and attributes. Preserve full attribute names in formats that support them and provide a mapping for Shapefile field-name limits.

Add meaningful integration tests: run-specific results cannot leak into another scenario, nodata never counts as dry/exposure-free, map statistics match exported data within documented tolerances, cached identity is correct, and a changed scenario requires a new run. Test the user journey against a genuine saved solver result. Synthetic UI fixtures must stay in a distinct example project with visible labels.

Show friendly unavailable/error/empty states when data or solvers are missing. Display 'hypothetical scenario' or 'historical replay' clearly without exposing unnecessary implementation detail to ordinary users. Keep technical provenance accessible in a details panel and report.

End with demonstrated workflows, files changed, commands/tests actually executed, screenshots where tooling allows, export paths, failures/skips, and remaining scientific gaps. Update PROJECT_STATE.md and the PS compliance matrix.
```

## Prompt 4 — Earth Engine, historical assessment, end-to-end verification, and handover

```text
Complete DamSafe phase 4 in the same repository. Read current repository instructions, status, input contracts, model-run evidence, validation plan and PS compliance. First resolve feasible outstanding core defects. Do not prioritize decorative UI over missing numerical engines, genuine comparison, required exports, or data quality.

Implement the PS's Google Earth Engine observation path using Sentinel-1 GRD, with explicit project/account setup through supported authentication and environment configuration. Do not expose tokens. If credentials/access are unavailable, provide the working configurable pipeline and an explicitly attributed import path for authentic exported observations, but mark live Earth Engine execution as unverified. Do not claim an import-only workflow satisfies a working near-real-time integration.

Use suitable pre-event and event acquisitions for the chosen Ujjani/Bhima domain. Filter compatible orbit direction/relative orbit, mode, polarization, footprint, and dates; inspect coverage. Use an explained flood-mapping method with permanent-water and unreliable-observation masks. Address speckle, radar shadow/layover and steep slopes where relevant. Handle dB versus linear backscatter correctly. Do not apply optical cloud masking as the SAR processing method. Sentinel-2 may be a secondary optical cross-check, not a compulsory second pipeline.

Persist scene identifiers, acquisition timestamps, processing time, method/thresholds, coverage and quality masks. Explain that new satellite observations depend on overpasses and ingestion; a daily collection update is not daily coverage of every location. Historical demonstration mode and latest-available observation mode must be visually distinct. Never fabricate a current observation when no suitable image exists.

Assess only a historical release/flood simulation that overlaps the observation in location, actual event time, hydraulic forcing and baseline definition. Compare the simulation at the image acquisition time, not its maximum-ever flood footprint, unless the reference explicitly represents an event maximum. Mask areas without reliable satellite interpretation; handle permanent water consistently. Compute confusion counts, IoU, precision, recall/F1 and area differences on a common valid grid, with explicit empty-mask behaviour. Call these agreement with a satellite-derived reference, which itself has errors. Keep calibration and assessment evidence separate: do not tune on the same event and call that independent validation. A release-event fit cannot establish accuracy for unobserved extreme failure scenarios.

Where independent water-level/discharge observations exist, check datum, location, timestamp and quality before calculating stage errors, peak/time differences and hydrograph comparisons. If adequate records do not exist, report insufficient evidence. Hypothetical failure runs must never receive an 'observed-event validated' badge from an unrelated monsoon image. Retain small benchmark and mesh/time-step sensitivity evidence from phase 2.

Run end-to-end verification with actual available engines and verified datasets: import, validate, snapshot scenario, execute, normalize, map, compare, exposure, observation assessment, and export. Validate volume balance and result identity. Test failure recovery, retry/cancellation and duplicate submission behaviour, state persistence after restart, isolation between projects/runs, bounded uploads and storage paths, and absence of secrets in logs or client bundles. Security changes must fit the deployment: local-only demo or authenticated access, not an unauthenticated publicly exposed upload/compute service.

Measure preprocessing, computation, postprocessing and playback separately on the actual hardware and domain/resolution. State what is precomputed or cached. Do not promise a real-time full-domain SPH computation without measurements. Profile and fix observed bottlenecks rather than adding infrastructure speculatively.

Prepare a reproducible local deployment/start command, environment template, pinned dependency/engine provenance, database migrations, sample commands, and data-fetch instructions. Do not push, merge, or publish without the relevant task authorization. Package small redistributable reference examples with their licences; provide external manifests for larger datasets/outputs. Avoid bundling restricted or unlicensed inputs.

Deliver docs/FINAL_READINESS.md, docs/DEMO_SCRIPT.md and docs/JUDGE_QA.md. The demo should show source/readiness, a real short run, a changed scenario, time/depth outputs, a valid local SPH/Delft comparison, historical observation assessment if supported, exposure and GIS export. Clearly label precomputed runs and the scope of every validation claim.

The final readiness report must separate: application works; each engine actually ran; Ujjani inputs verified; Ujjani simulation ran; both models compared on compatible site data; historical event assessed; Google Earth Engine executed; exports verified; loss estimation supported; and domain expert review obtained. Mark each PASS/PARTIAL/BLOCKED/DEFERRED with evidence. A test skip is not a pass. Missing data, native binaries, or independent observations mean the corresponding scientific deliverable is incomplete, even if the application build passes.

Document remaining PS scope: natural river blockage modelling, debris/erosion, generalized rainfall-runoff, and full-domain 3D SPH remain deferred unless actually implemented and tested. Do not claim full PS compliance by weakening the requirements. If two-engine site comparison scope needs sponsor clarification, state that explicitly.

Finish all feasible authorized implementation before reporting blockers. End with a concise user-facing outcome: what runs now, how to start it, what was actually tested, which exact external inputs remain, and whether it is demonstrable versus scientifically assessed. Do not claim the whole project is finished solely because this is prompt 4.
```

## Evidence and source notes

- The uploaded PRD is the source for the section-specific review. No repository was supplied or audited in this review.
- [Official Ujjani discharge catalogue](https://www.nwdp.nwic.gov.in/dataset/reservoir_discharge_ujjani_dam_1_maharashtra_telemetry_hourly): a dataset lead, not an audited input file.
- [Deltares Delft3D source](https://github.com/Deltares/Delft3D): official engine family and build documentation. Check the selected release's actual supported workflow.
- [DualSPHysics source](https://github.com/DualSPHysics/DualSPHysics): official SPH implementation and CPU/GPU build guidance.
- [USACE: Using HEC-RAS for Dam Break Studies](https://www.hec.usace.army.mil/publications/TrainingDocuments/TD-39.pdf): background on reservoir routing, breach assumptions and downstream hydraulics; HEC-RAS is not substituted for the required engines here.
- [Earth Engine Sentinel-1 GRD catalogue](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD): processing, imagery characteristics and ingestion timing. Satellite reference maps have observation and classification limitations.

**What we should do next:** run prompt 1 in the intended repository and review its actual dataset/engine evidence before expecting the subsequent stages to deliver a credible Ujjani result.
