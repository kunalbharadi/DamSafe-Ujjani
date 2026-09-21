import React, { useState } from 'react';
import type { GaugeResult, NumericalRun, ObsResult, Project, ValidationResult } from '../types';
import { StatusBadge, DataRequiredBox } from '../components/StatusBadge';
import { compareSatellite, evaluateGauge, queryGeeObservation } from '../api';

type ValidationProps = {
  project: Project | null;
  runs: NumericalRun[];
  onError: (e: string) => void;
  onNotice: (n: string) => void;
};

export function Validation({ project, runs, onError, onNotice }: ValidationProps) {
  const [obsMode, setObsMode] = useState<'HISTORICAL_EVENT' | 'LATEST_AVAILABLE'>('HISTORICAL_EVENT');
  const [obsResult, setObsResult] = useState<ObsResult | null>(null);
  const [obsLoading, setObsLoading] = useState(false);

  const [selectedRunId, setSelectedRunId] = useState('');
  const [valResult, setValResult] = useState<ValidationResult | null>(null);
  const [valLoading, setValLoading] = useState(false);

  const [gaugeResult, setGaugeResult] = useState<GaugeResult | null>(null);
  const [gaugeLoading, setGaugeLoading] = useState(false);

  const succeededRuns = runs.filter((r) => r.state === 'SUCCEEDED');
  const selectedRun = runs.find((r) => r.id === selectedRunId);

  async function handleQueryObs() {
    setObsLoading(true);
    try {
      const result = await queryGeeObservation(obsMode);
      setObsResult(result);
    } catch (e) {
      onError(String(e));
    } finally {
      setObsLoading(false);
    }
  }

  async function handleComputeAgreement() {
    if (!project || !selectedRunId) return;
    setValLoading(true);
    try {
      const result = await compareSatellite(project.id, selectedRunId, obsMode);
      setValResult(result);
    } catch (e) {
      // Surface the error as a validation result (not validated)
      setValResult({ status: 'NOT_VALIDATED', note: String(e) });
      onError(String(e));
    } finally {
      setValLoading(false);
    }
  }

  async function handleEvaluateGauge() {
    if (!project || !selectedRunId) return;
    setGaugeLoading(true);
    try {
      const result = await evaluateGauge(project.id, selectedRunId, 'station-001');
      setGaugeResult(result);
    } catch (e) {
      onError(String(e));
    } finally {
      setGaugeLoading(false);
    }
  }

  const agreement = valResult?.agreement as {
    TP: number; FP: number; FN: number; TN: number;
    IoU: number; precision: number; recall: number; F1: number;
  } | undefined;

  return (
    <div id="page-validation">
      <div className="page-header">
        <div className="page-eyebrow">⑥ Validation</div>
        <h1 className="page-title">Satellite &amp; Gauge Validation</h1>
        <p className="page-subtitle">
          Compare simulation results against Sentinel-1 satellite observations and gauge recordings.
          No scores are fabricated — missing data shows DATA REQUIRED.
        </p>
      </div>

      {/* Sentinel-1 observation section */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">🛰 Sentinel-1 Earth Engine Observation</span>
          <span className="badge badge-blue">SAR / GEE</span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
            Query authenticated Sentinel-1 GRD observation metadata for the Ujjani–Bhima reach.
            Historical event: October 2020 Bhima flood. Authentication readiness and observation
            status are separated.
          </p>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 16 }}>
            <div className="form-group" style={{ marginBottom: 0, minWidth: 280 }}>
              <label className="form-label">Observation Mode</label>
              <select
                id="obs-mode-select"
                className="form-select"
                value={obsMode}
                onChange={(e) => setObsMode(e.target.value as typeof obsMode)}
              >
                <option value="HISTORICAL_EVENT">HISTORICAL_EVENT — October 2020 Bhima Flood</option>
                <option value="LATEST_AVAILABLE">LATEST_AVAILABLE — Most Recent Overpass</option>
              </select>
            </div>
            <button
              id="btn-query-observation"
              className="btn btn-primary"
              onClick={handleQueryObs}
              disabled={obsLoading}
            >
              {obsLoading ? <span className="spinner" /> : '🛰'} Query Satellite Observation
            </button>
          </div>

          {obsResult ? (
            <div className="card" style={{ background: '#F8FAFC' }}>
              <div className="card-body">
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
                  <StatusBadge value={obsResult.execution_state} />
                  <span className="badge badge-blue">{obsResult.provenance_type}</span>
                </div>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Observation ID</span>
                    <span className="detail-value"><code style={{ fontSize: 11 }}>{obsResult.observation_id}</code></span>
                  </div>
                  {obsResult.scene_info && (
                    <div className="detail-item">
                      <span className="detail-label">Scene ID</span>
                      <span className="detail-value" style={{ fontSize: 12 }}>
                        <code>{obsResult.scene_info.scene_id}</code>
                        {' '}(Orbit {obsResult.scene_info.relative_orbit}, {obsResult.scene_info.orbit_direction})
                      </span>
                    </div>
                  )}
                  {obsResult.acquisition_time && (
                    <div className="detail-item">
                      <span className="detail-label">Acquisition (UTC)</span>
                      <span className="detail-value">{obsResult.acquisition_time}</span>
                    </div>
                  )}
                  <div className="detail-item">
                    <span className="detail-label">Flooded Area</span>
                    <span className="detail-value">
                      {obsResult.flooded_area_km2 != null ? `${obsResult.flooded_area_km2} km²` : 'N/A'}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Permanent Water</span>
                    <span className="detail-value">
                      {obsResult.permanent_water_area_km2 != null ? `${obsResult.permanent_water_area_km2} km²` : 'N/A'}
                    </span>
                  </div>
                </div>
                {obsResult.notes && (
                  <p style={{ fontSize: 12, color: '#64748B', marginTop: 12 }}>{obsResult.notes}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: 20 }}>
              <div className="empty-state-text">
                No observation queried. Press "Query Satellite Observation" to retrieve authentic metadata.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Satellite agreement section */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">📊 Simulation–Satellite Agreement</span>
          <span className="badge badge-gray">Cell-by-cell spatial comparison</span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
            Evaluates cell-by-cell spatial agreement between a selected numerical simulation run and a
            Sentinel-1 satellite flood reference. Labeled strictly as "agreement with satellite-derived flood reference"
            — not absolute accuracy.
          </p>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 16 }}>
            <div className="form-group" style={{ marginBottom: 0, minWidth: 300 }}>
              <label className="form-label">Numerical Run</label>
              <select
                id="val-run-select"
                className="form-select"
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
              >
                <option value="">— Select a succeeded run —</option>
                {succeededRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 16)}… · {r.input.request.engine}
                  </option>
                ))}
              </select>
            </div>
            <button
              id="btn-compute-agreement"
              className="btn btn-primary"
              disabled={valLoading || !selectedRunId || !project}
              onClick={handleComputeAgreement}
            >
              {valLoading ? <span className="spinner" /> : '📊'} Compute Agreement Metrics
            </button>
          </div>

          {/* Metrics or DATA REQUIRED */}
          {valResult ? (
            <div>
              {agreement ? (
                <>
                  <div className="metric-grid">
                    {[
                      { name: 'TP', value: agreement.TP, unit: 'cells' },
                      { name: 'FP', value: agreement.FP, unit: 'cells' },
                      { name: 'FN', value: agreement.FN, unit: 'cells' },
                      { name: 'TN', value: agreement.TN, unit: 'cells' },
                      { name: 'IoU', value: agreement.IoU.toFixed(3), unit: 'Jaccard index' },
                      { name: 'Precision', value: agreement.precision.toFixed(3), unit: 'TP/(TP+FP)' },
                      { name: 'Recall', value: agreement.recall.toFixed(3), unit: 'TP/(TP+FN)' },
                      { name: 'F1', value: agreement.F1.toFixed(3), unit: 'harmonic mean' },
                    ].map((m) => (
                      <div key={m.name} className="metric-card">
                        <div className="metric-name">{m.name}</div>
                        <div className="metric-value">{m.value}</div>
                        <div className="metric-unit">{m.unit}</div>
                      </div>
                    ))}
                  </div>
                  <p className="caption" style={{ marginTop: 8 }}>
                    These are spatial agreement statistics between the simulation and satellite-derived flood reference.
                    They are not absolute flood prediction accuracy scores.
                  </p>
                </>
              ) : (
                <div>
                  <DataRequiredBox
                    label="NOT VALIDATED"
                    reason={valResult.note ?? valResult.limitation as string ?? 'Satellite grid unavailable for comparison. Run satellite query first.'}
                  />
                  {valResult.note && (
                    <pre className="json-pre" style={{ marginTop: 12 }}>{JSON.stringify(valResult, null, 2)}</pre>
                  )}
                </div>
              )}
            </div>
          ) : (
            <DataRequiredBox
              label="NOT VALIDATED"
              reason="Select a successful run and compute agreement metrics. Requires satellite observation query first."
            />
          )}
        </div>
      </div>

      {/* Three-panel comparison placeholder */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">🖼 Spatial Comparison (Three-Panel)</span>
          <span className="badge badge-data-required">DATA REQUIRED</span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {['Simulation Flood Extent', 'Satellite Observation', 'Overlay (Agree / Disagree)'].map((label) => (
              <div key={label} style={{
                height: 180, background: '#F1F5F9', borderRadius: 8,
                display: 'grid', placeItems: 'center', border: '1px dashed #CBD5E1',
                fontSize: 12, color: '#64748B', textAlign: 'center', padding: 12,
              }}>
                <div>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>🗺</div>
                  <strong>{label}</strong>
                  <p style={{ marginTop: 4 }}>Requires geospatial grid data from both simulation and satellite</p>
                </div>
              </div>
            ))}
          </div>
          <p className="caption" style={{ marginTop: 12 }}>
            Side-by-side spatial comparison requires compatible geospatial grids from the simulation and the satellite observation.
            Available once spatial grid data is confirmed compatible.
          </p>
        </div>
      </div>

      {/* Gauge evaluation */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">📡 Gauge Hydrograph Evaluation</span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
            Compares simulated stage and discharge hydrographs against independent river gauge recordings.
            Station 001 is the currently configured evaluation gauge.
          </p>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              id="btn-evaluate-gauge"
              className="btn btn-outline-orange"
              disabled={gaugeLoading || !selectedRunId || !project}
              onClick={handleEvaluateGauge}
            >
              {gaugeLoading ? <span className="spinner" /> : '📡'} Evaluate Gauge Station 001
            </button>
            {!selectedRunId && (
              <span className="caption">Select a run above first</span>
            )}
          </div>
          {gaugeResult ? (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                <StatusBadge value={gaugeResult.status} />
                <code style={{ fontSize: 12 }}>{gaugeResult.station_id}</code>
              </div>
              {gaugeResult.note && (
                <p style={{ fontSize: 13, color: '#64748B' }}>{gaugeResult.note}</p>
              )}
              <pre className="json-pre">{JSON.stringify(gaugeResult, null, 2)}</pre>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: 20, textAlign: 'left' }}>
              <span style={{ fontSize: 12, color: '#94A3B8' }}>
                No gauge evaluation run. Press "Evaluate Gauge Station 001" after selecting a run.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
