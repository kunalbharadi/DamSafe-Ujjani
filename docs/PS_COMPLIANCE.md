# PS 26161 deliverable evidence matrix

This maps the supplied implementation brief's interpretation of PS 26161. The original official PS and the full PRD were not present. Status uses implemented/tested/blocked/deferred; a blocked row may have preparatory code but is not a completed deliverable.

| Deliverable | Status | Code / evidence | Missing completion evidence |
| --- | --- | --- | --- |
| Reusable input contracts / provenance | tested | `contracts.py`, `ingestion.py`, `storage.py`; software tests | Broader data/provider formats; production S3 verification |
| Real Ujjani data audit | tested | Raw NWIC downloads; `evidence/*audit.json` | Physical pathway, timezone and event suitability unresolved |
| Project/scenario/dataset API | tested | `api.py`, SQLAlchemy persistence and snapshot tests | PostgreSQL runtime verification |
| Input-readiness interface | tested | React/TypeScript setup UI and backend checks | Hydraulic interpretation review and derived-domain setup |
| PostgreSQL/PostGIS service and migrations | tested locally | Docker Compose PostGIS 16/3.5, migration and `PostGIS_Version()` query | Production deployment and concurrent load not assessed |
| Background queue | tested locally | SQL audit and numerical workers; bounded/cancellable execution, stale-lease recovery tests | Production worker supervision and load limits still require review |
| Immutable hydraulic run manifest contract | tested locally | `runs` table, input update/delete trigger, idempotent API, execution/result separation | Imported-output workflow and production concurrency not implemented |
| D-Flow FM actual execution | tested locally | Pinned runtime image, exact official f34 case, lake-at-rest and shared native runs; `PHASE2_EVIDENCE.md` | Ujjani domain and forcing absent; local analytical check does not validate site |
| DualSPHysics actual execution | tested locally | Real CPU image, original official 0.01 m run, 0.02 m automatic solver-to-normalized run; `PHASE2_EVIDENCE.md` | Mass loss and literature-reference interpretation prevent validation claim |
| Computed breach/reservoir routing | blocked | Separate typed contract and analytical prescribed-pathway storage balance | Verified component/method, level–storage and all physical release inputs |
| Compatible SPH/D-Flow benchmark comparison | tested locally | Physically matched synthetic closed-tank case, depth/extent/runtime agreement report | Breaking/impact interpretation and SPH mass loss limit validation; no site comparison |
| Compatible Ujjani site comparison | blocked | One-site scope retained | Verified site inputs and two genuine local runs |
| Depth/velocity normalization | tested locally for both engines | Genuine SPH PartVTK and D-Flow face-centred map outputs to NetCDF | Ujjani mesh/forcing absent; SPH local impact zones require interpretation |
| Ujjani arrival/duration outputs | blocked | No site result generator exists | Two actual site-specific runs, phase 3 output derivation |
| Exposure assessment | blocked | Vector import only | Verified layers and hydraulic results, phase 3 |
| Economic losses | blocked | Deliberately unavailable | Asset values and applicable vulnerability functions |
| GeoTIFF/KML/GeoJSON/Shapefile/CSV/report exports | blocked | No export code claimed | Numerical results and independently reopened outputs, phase 3 |
| Google Earth Engine near-real-time path | blocked | Planned observation contract | Account/project/access and pipeline execution, phase 4 |
| Historical event assessment | blocked | Validation plan | Matching release, independent observations and executed model |
| Uncertainty ensemble / response priorities | blocked | Immutable scenario basis only | Actual ensemble runs and explanation metrics |
| Local demonstration | implemented | `scripts/start.ps1 -Preview`, Ujjani setup UI | Scientific demonstrator remains incomplete |
| Natural river blockage / erosion / debris | deferred | Explicit supplied scope | Separate modelling work |
| Rainfall-runoff generation | deferred | Prescribed/derived release scope | Separate hydrological model |
| Full-river 3D SPH / two-way coupling | deferred | Local comparison interpretation | Confirm spatial comparison expectation with sponsor |

There is no full PS compliance claim. Imported authentic numerical outputs, if added later, must have origin/engine/parameters/input hashes and cannot prove automatic execution. No synthetic flood layer or sample rupee loss is used to fill these gaps.
