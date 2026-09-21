// ─── DamSafe — Centralized API Layer ─────────────────────────────────────────
// All fetch calls go through here. No mocking, no fabrication.
// Backend base: /api (proxied by Vite in dev; served directly in prod)

import type {
  Dataset, Ensemble, ExposureResult, GaugeResult, HealthStatus,
  LocationSeries, NumericalRun, ObsResult, ProductArea, Project,
  Readiness, ResultMetadata, ResultWindow, Scenario, ValidationResult,
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    throw new Error(detail);
  }
  return data as T;
}

// ─── Health ──────────────────────────────────────────────────────────────────
export const getHealth = () => request<HealthStatus>('/health');

// ─── Projects ────────────────────────────────────────────────────────────────
export const listProjects = () => request<Project[]>('/projects');
export const getProject = (id: string) => request<Project>(`/projects/${id}`);
export const createProject = (body: unknown) =>
  request<Project>('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

// ─── Datasets ────────────────────────────────────────────────────────────────
export const listDatasets = (projectId: string) =>
  request<Dataset[]>(`/projects/${projectId}/datasets`);

export const uploadDataset = (
  projectId: string,
  file: File,
  metadataJson: string
) => {
  const params = new URLSearchParams({
    filename: file.name,
    metadata_json: metadataJson,
  });
  return request<Dataset>(`/projects/${projectId}/datasets?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: file,
  });
};

// ─── Readiness ───────────────────────────────────────────────────────────────
export const getReadiness = (projectId: string, scenarioId?: string) => {
  const params = scenarioId ? `?scenario_id=${scenarioId}` : '';
  return request<Readiness>(`/projects/${projectId}/readiness${params}`);
};

export const submitReadinessJob = (projectId: string) =>
  request<{ id: string; state: string }>(`/projects/${projectId}/readiness-jobs`, { method: 'POST' });

export const listJobs = (projectId: string) =>
  request<{ id: string; state: string; body: unknown }[]>(`/projects/${projectId}/jobs`);

// ─── Scenarios ───────────────────────────────────────────────────────────────
export const listScenarios = (projectId: string) =>
  request<Scenario[]>(`/projects/${projectId}/scenarios`);

export const createScenario = (projectId: string, body: unknown) =>
  request<Scenario>(`/projects/${projectId}/scenarios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

// ─── Numerical Runs ──────────────────────────────────────────────────────────
export const listRuns = (projectId: string) =>
  request<NumericalRun[]>(`/projects/${projectId}/runs`);

export const submitRun = (projectId: string, body: unknown) =>
  request<NumericalRun>(`/projects/${projectId}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

export const cancelRun = (projectId: string, runId: string) =>
  request(`/projects/${projectId}/runs/${runId}/cancel`, { method: 'POST' });

// ─── Results ─────────────────────────────────────────────────────────────────
const ALL_CELLS = '-1000000000,-1000000000,1000000000,1000000000';

export const getResultMetadata = (projectId: string, runId: string) =>
  request<ResultMetadata>(`/projects/${projectId}/runs/${runId}/results/metadata`);

export const getResultWindow = (
  projectId: string,
  runId: string,
  field: string,
  firstFrame: number,
  frameCount: number,
  bbox = ALL_CELLS
) =>
  request<ResultWindow>(
    `/projects/${projectId}/runs/${runId}/results/window?bbox=${bbox}&field=${field}&first_frame=${firstFrame}&frame_count=${frameCount}`
  );

export const getProductArea = (projectId: string, runId: string, firstFrame = 0, frameCount = 32) =>
  request<ProductArea>(
    `/projects/${projectId}/runs/${runId}/products/area?first_frame=${firstFrame}&frame_count=${frameCount}`
  );

export const getLocationSeries = (
  projectId: string, runId: string,
  name: string, x: number, y: number, radiusM: number
) =>
  request<LocationSeries>(
    `/projects/${projectId}/runs/${runId}/products/location?name=${encodeURIComponent(name)}&x=${x}&y=${y}&radius_m=${radiusM}`
  );

export const compareRuns = (projectId: string, runIdA: string, runIdB: string) =>
  request<Record<string, unknown>>(`/projects/${projectId}/runs/${runIdA}/compare/${runIdB}`);

// ─── Ensembles ───────────────────────────────────────────────────────────────
export const listEnsembles = (projectId: string) =>
  request<Ensemble[]>(`/projects/${projectId}/ensembles`);

export const submitEnsemble = (projectId: string, body: unknown) =>
  request<Ensemble>(`/projects/${projectId}/ensembles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

export const getEnsembleSummary = (projectId: string, ensembleId: string) =>
  request<Record<string, unknown>>(`/projects/${projectId}/ensembles/${ensembleId}/summary`);

// ─── Exports ─────────────────────────────────────────────────────────────────
export async function downloadExport(
  projectId: string,
  runId: string,
  format: string
): Promise<void> {
  const response = await fetch(`/api/projects/${projectId}/runs/${runId}/exports/${format}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${runId}-${format}`;
  link.click();
  URL.revokeObjectURL(url);
}

// ─── Observations & Validation ───────────────────────────────────────────────
export const queryGeeObservation = (
  mode: 'HISTORICAL_EVENT' | 'LATEST_AVAILABLE'
) =>
  request<ObsResult>(`/observation/gee/query?site_key=ujjani-bhima&mode=${mode}`, {
    method: 'POST',
  });

export const compareSatellite = (
  projectId: string,
  runId: string,
  mode: 'HISTORICAL_EVENT' | 'LATEST_AVAILABLE'
) =>
  request<ValidationResult>(
    `/projects/${projectId}/runs/${runId}/compare_satellite?mode=${mode}`,
    { method: 'POST' }
  );

export const evaluateGauge = (projectId: string, runId: string, stationId: string) =>
  request<GaugeResult>(`/projects/${projectId}/runs/${runId}/gauges/${stationId}`);

// ─── Exposure / Impact ───────────────────────────────────────────────────────
export const getExposure = (projectId: string, runId: string) =>
  request<ExposureResult>(`/projects/${projectId}/runs/${runId}/exposure`);

// ─── SPH ─────────────────────────────────────────────────────────────────────
export const listSphRuns = () =>
  request<{ runs: string[] }>('/sph/runs');
