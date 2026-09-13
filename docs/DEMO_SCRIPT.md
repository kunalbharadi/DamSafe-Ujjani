# DamSafe — SIH Judging Demo Script

This script provides a verified, step-by-step walkthrough for demonstrating DamSafe during SIH evaluation.

---

## Prerequisites & Startup

Start the local DamSafe development stack:
```powershell
.\scripts\start.ps1 -Preview
```
This starts the backend API, SQLite database, background workers, and serves the production-built React frontend at:
`http://127.0.0.1:8000`

---

## 17-Step Demo Sequence

1. **Open Application**:
   - Navigate to `http://127.0.0.1:8000` in the browser.
   - Point out the active study domain: **Ujjani Reservoir / Bhima River Basin** (EPSG:4326).

2. **Demonstrate Project Provenance**:
   - Inspect the study domain bounding box on the 2D MapLibre viewer (`74.6°E to 75.1°E, 18.0°N to 18.4°N`).
   - Note the clear indicator: *No validated Ujjani flood prediction exists in this workspace.*

3. **Show Scientific Readiness & Compliance Findings**:
   - Click the **Readiness** tab.
   - Point out findings: missing sub-surface bathymetry, uncalibrated spillway rating curves, unaligned gauge datums.
   - Highlight DamSafe's design philosophy: missing data is reported as `BLOCKED`/`UNAVAILABLE` rather than faked.

4. **Show Verified Source Inputs**:
   - Click the **Data library** tab.
   - Review imported datasets with cryptographic SHA-256 hashes, provenance tags, and unit metadata.

5. **Show Immutable Scenario Contract**:
   - Click the **Scenarios** tab.
   - Inspect JSON scenario contracts with explicit simulation start/end times and boundary conditions.

6. **Run Official Engine Example (Laboratory Benchmarks)**:
   - Click **Numerical runs** -> Click **Open laboratory project**.
   - Select `DualSPHysics` or `D-Flow FM` and click **Run official laboratory example** (`[LIVE EXECUTION]`).

7. **Show Real-time Execution & Progress State**:
   - Observe live worker status transition: `QUEUED` -> `RUNNING` -> `SUCCEEDED`.

8. **Explore Depth, Velocity, & Arrival Results**:
   - Click **Explore results** on the completed run.
   - View maximum depth (e.g. `0.850 m`), wet cell count, simulation elapsed time, and animated grid playback (`[PRECOMPUTED / LIVE NORMALIZED RESULT]`).

9. **Scenario Parameter Variant Sensitivity**:
   - Click the **Ensembles** tab.
   - Submit an ensemble of particle spacing variants (`0.01m` vs `0.02m`).
   - Emphasize that ensemble statistics report **scenario frequency**, not statistical probability.

10. **Compare Numerical Runs**:
    - Click the **Compare** tab.
    - Select Run A and Run B to compute cell-by-cell numerical depth differences on a shared grid contract.

11. **Explain Two-Engine Hydraulic Roles (D-Flow FM vs DualSPHysics)**:
    - Explain that D-Flow FM computes 2D regional shallow water equations across downstream valleys, while DualSPHysics resolves 3D near-field turbulent dam collapse and structure impact.
    - Point out that site-wide two-engine comparison is currently `BLOCKED` due to absence of verified site mesh.

12. **Query Sentinel-1 Satellite Observations**:
    - Click the **Observations** tab.
    - Select `HISTORICAL_EVENT` mode and click **Query Observation**.
    - Review Sentinel-1 GRD acquisition parameters, speckle filtering, and validity masks.

13. **Compute Satellite Flood Agreement Metrics**:
    - Click the **Validation** tab.
    - Click **Compute Satellite Agreement Metrics**.
    - Review IoU (Jaccard Index), Precision, Recall, F1-Score, and Confusion Matrix (`TP`, `FP`, `FN`, `TN`), labeled strictly as *agreement with satellite-derived flood reference*.

14. **Evaluate Independent Gauge Hydrographs**:
    - In the **Validation** tab, click **Evaluate Gauge Station 001**.
    - Observe the honest status: `INSUFFICIENT_EVIDENCE` due to missing zero-datum alignment.

15. **Evaluate Exposure & Inundation Overlay**:
    - Click the **Exposure** tab.
    - Click **Evaluate Exposure & Loss**.
    - Inspect settlement inundation count (14 villages) and agricultural land (4,250 ha), while population remains `UNAVAILABLE` and economic loss is `BLOCKED`.

16. **Generate GIS Exports**:
    - Under Results, click **Download GeoTIFF**, **Download GeoJSON**, and **Download CSV**.

17. **Conclude on Scientific Readiness & Boundaries**:
    - Summarize that DamSafe enforces scientific honesty: synthetic laboratory evidence is not site validation, missing data returns `UNAVAILABLE`/`BLOCKED`, and software readiness (`PASS`) is distinct from operational deployment (`BLOCKED`).
