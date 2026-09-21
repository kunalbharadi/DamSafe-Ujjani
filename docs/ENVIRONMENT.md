# Environment and credentials

The local dashboard, OpenStreetMap context map, Three.js viewers, saved results and GIS exports need **no API key**. Fresh numerical execution requires Docker Desktop's Linux engine and the pinned D-Flow FM / DualSPHysics images and source checkouts described in ENGINE_AUDIT.md.

## Local configuration

`scripts/start.ps1 -Preview` creates .env from .env.example only when missing. The Python package loads that file without overriding existing process variables. The preview launcher sets the SQLite database and storage path. .env and credential files must stay outside commits. Never put secrets in VITE_ variables: those are visible in browser bundles.

## Google Earth Engine

Live queries require a Google Cloud project registered for Earth Engine, the Earth Engine API enabled, and an account permitted to use that project. This uses OAuth or a service account, **not a simple API-key string**.

1. Put the Google Cloud project ID in `EE_PROJECT` in your local .env.
2. For your local interactive account, leave `EE_SERVICE_ACCOUNT_JSON` empty and run:

```powershell
.\.venv\Scripts\earthengine.exe authenticate
```

3. Alternatively, for unattended execution, keep a service-account JSON outside this repository and set `EE_SERVICE_ACCOUNT_JSON` to its absolute path. Give that account the necessary project/Earth Engine permissions.
4. Restart DamSafe after changing .env.

Provider errors are redacted; credentials are not returned to the browser. Authentication wiring has unit tests with mocked credentials. Live Earth Engine execution remains **unverified** until an authorized account completes a real query. Current live query code discovers scenes; this is not a completed near-real-time flood classification and assessment service. Satellite coverage depends on overpass and ingestion, not a promise of daily coverage.

Official instructions: [authentication](https://developers.google.com/earth-engine/guides/auth), [service accounts](https://developers.google.com/earth-engine/guides/service_account).

## Other services

- Google Maps, Cesium ion, Mapbox, OpenAI and Gemini keys are not consumed by the current application. Adding them does not enable terrain or numerical solvers.
- The Docker Compose stack uses `POSTGRES_PASSWORD`; choose your own value for shared development. The API remains loopback-only; public deployment requires authentication.
- S3 is optional. Use the backend storage configuration and standard AWS credentials only if deploying to S3. Local preview requires neither.
- The current Compose file does not mount personal Earth Engine credentials. Use the Windows preview for the documented OAuth setup; configure container credential mounts explicitly for a container deployment.

## External inputs still required

Verified bathymetry/cross-sections, reservoir storage and structure data, continuous release/inflow and downstream boundary series, independent gauge data with datum/quality/timezone, authentic matched SAR observations, and licensed asset/population layers are data requirements. An API key cannot replace them.
