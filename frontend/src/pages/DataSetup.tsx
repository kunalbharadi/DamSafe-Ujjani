import React, { useRef, useState } from 'react';
import type { Dataset, Finding, Job, Project, Readiness } from '../types';
import { StatusBadge, DataRequiredBox } from '../components/StatusBadge';
import { uploadDataset, submitReadinessJob } from '../api';

type DataSetupProps = {
  project: Project | null;
  datasets: Dataset[];
  readiness: Readiness | null;
  jobs: Job[];
  onRefresh: () => void;
  onError: (e: string) => void;
  onNotice: (n: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
};

type CategoryStatus = 'AVAILABLE' | 'ASSUMPTION' | 'DATA REQUIRED' | 'BLOCKED';

type DataCategory = {
  id: string;
  name: string;
  icon: string;
  desc: string;
  kinds: string[];
  findingCode?: string;
};

const CATEGORIES: DataCategory[] = [
  {
    id: 'terrain',
    name: 'Terrain / DEM',
    icon: '🏔',
    desc: 'SRTM, ASTER or surveyed DEM. Required for hydrodynamic mesh generation.',
    kinds: ['terrain'],
    findingCode: 'TERRAIN',
  },
  {
    id: 'dam',
    name: 'Dam Specifications',
    icon: '🏗',
    desc: 'Dam height, crest elevation, breach parameters, and structural geometry.',
    kinds: ['dam_geometry'],
    findingCode: 'DAM',
  },
  {
    id: 'hydrology',
    name: 'Hydrological Inputs',
    icon: '💧',
    desc: 'Inflow hydrographs, reservoir level records, discharge time series.',
    kinds: ['hydrology'],
    findingCode: 'HYDRO',
  },
  {
    id: 'geometry',
    name: 'River Geometry',
    icon: '〰',
    desc: 'Cross-sections, bathymetry, channel networks, reach delineation.',
    kinds: ['geometry', 'river'],
    findingCode: 'GEOMETRY',
  },
  {
    id: 'satellite',
    name: 'Satellite Observations',
    icon: '🛰',
    desc: 'Sentinel-1 SAR flood extent for validation. Queried via Google Earth Engine.',
    kinds: ['observation'],
    findingCode: 'SAR',
  },
  {
    id: 'gauge',
    name: 'Gauge / Boundary Conditions',
    icon: '📡',
    desc: 'River gauge observations for boundary conditions and calibration.',
    kinds: ['gauge', 'boundary'],
    findingCode: 'GAUGE',
  },
];

function categoryStatus(
  category: DataCategory,
  datasets: Dataset[],
  readiness: Readiness | null
): CategoryStatus {
  const matched = datasets.filter((d) => category.kinds.includes(d.kind));
  if (matched.length === 0) {
    // Check if blocked by readiness
    if (readiness?.missing.some((f) => f.code.includes(category.findingCode ?? ''))) return 'BLOCKED';
    return 'DATA REQUIRED';
  }
  if (matched.some((d) => d.provenance.status === 'assumed')) return 'ASSUMPTION';
  return 'AVAILABLE';
}

const DEFAULT_META = JSON.stringify({
  name: 'discharge_series',
  kind: 'hydrology',
  provenance: {
    source_url: 'https://example.gov/data',
    agency: 'CWC India',
    licence: 'Government of India Open Data',
    acquisition_date: null,
    acquisition_date_note: 'Acquisition period must be verified from source',
    units: 'm3/s',
    crs: null,
    vertical_reference: null,
    processing_history: [],
    status: 'assumed',
    synthetic: false,
  },
  hydro: {
    station_id: 'station-001',
    source_timezone: 'Asia/Kolkata',
    measurement: 'river_outflow',
    identity_reference: null,
    interval_seconds: 3600,
  },
}, null, 2);

export function DataSetup({
  project, datasets, readiness, jobs, onRefresh, onError, onNotice, busy, setBusy,
}: DataSetupProps) {
  const [file, setFile] = useState<File | null>(null);
  const [metaJson, setMetaJson] = useState(DEFAULT_META);
  const [showUpload, setShowUpload] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const latestJob = jobs[jobs.length - 1];
  const totalScore = readiness
    ? Math.max(0, 100 - readiness.missing.length * 15 - readiness.warnings.length * 5)
    : null;

  async function handleAudit() {
    if (!project) return;
    setBusy(true);
    try {
      await submitReadinessJob(project.id);
      await onRefresh();
      onNotice('Readiness audit queued. This audits data inputs, not a hydraulic solver.');
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload() {
    if (!project || !file) { onError('Choose a file first'); return; }
    setBusy(true);
    try {
      JSON.parse(metaJson); // Validate JSON before submitting
      await uploadDataset(project.id, file, metaJson);
      await onRefresh();
      onNotice('Dataset uploaded and validated. Review findings before modelling.');
      setFile(null);
      setShowUpload(false);
      if (fileRef.current) fileRef.current.value = '';
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div id="page-data-setup">
      <div className="page-header">
        <div className="page-eyebrow">② Data Setup</div>
        <h1 className="page-title">Input Data &amp; Readiness</h1>
        <p className="page-subtitle">
          Review data availability across all required categories. Upload missing datasets.
          Run a readiness audit to identify gaps before simulation.
        </p>
        <div className="page-actions">
          <button
            id="btn-run-audit"
            className="btn btn-primary"
            disabled={busy || !project}
            onClick={handleAudit}
          >
            {busy ? <span className="spinner" /> : '🔍'} Run Readiness Audit
          </button>
          <button
            id="btn-add-dataset"
            className="btn btn-outline-orange"
            disabled={!project}
            onClick={() => setShowUpload(!showUpload)}
          >
            + Add Dataset
          </button>
        </div>
      </div>

      {/* Readiness summary */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-label">Overall Readiness</div>
          <div className={`stat-value ${totalScore !== null && totalScore >= 70 ? 'green' : 'orange'}`}>
            {totalScore !== null ? `${totalScore}%` : '—'}
          </div>
          <div className="stat-sub">Based on missing &amp; warning findings</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Datasets Imported</div>
          <div className="stat-value">{datasets.length.toString().padStart(2, '0')}</div>
          <div className="stat-sub">Versioned with SHA-256 checksums</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Missing Inputs</div>
          <div className={`stat-value ${(readiness?.missing.length ?? 0) > 0 ? 'orange' : 'green'}`}>
            {readiness?.missing.length ?? '—'}
          </div>
          <div className="stat-sub">
            {latestJob ? `Last audit: ` : 'No audit run yet'}
            {latestJob && <StatusBadge value={latestJob.state} />}
          </div>
        </div>
      </div>

      {/* Data categories grid */}
      <div className="readiness-grid">
        {CATEGORIES.map((cat) => {
          const status = categoryStatus(cat, datasets, readiness);
          const catDatasets = datasets.filter((d) => cat.kinds.includes(d.kind));
          return (
            <div key={cat.id} className="readiness-category">
              <div className="readiness-icon">{cat.icon}</div>
              <div className="readiness-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span className="readiness-name">{cat.name}</span>
                  <StatusBadge value={status} />
                </div>
                <div className="readiness-desc">{cat.desc}</div>
                {catDatasets.length > 0 && (
                  <div style={{ marginTop: 8, fontSize: 11, color: '#64748B' }}>
                    {catDatasets.map((d) => (
                      <div key={d.id}>
                        ✓ {d.name} <span style={{ color: '#94A3B8' }}>v{d.version}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Upload panel (expandable) */}
      {showUpload && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <span className="card-title">Add Immutable Dataset Version</span>
            <button className="btn btn-sm" onClick={() => setShowUpload(false)}>✕ Close</button>
          </div>
          <div className="card-body">
            <p style={{ fontSize: 12, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
              Upload is connected to the ingestion API. The server validates format, provenance, units, and limits before storing a SHA-256 checksum.
              Accepted: CSV (hydrology), GeoTIFF (terrain), GeoJSON/GeoPackage (geometry).
            </p>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Data File</label>
                <input
                  id="upload-file"
                  ref={fileRef}
                  type="file"
                  accept=".csv,.tif,.tiff,.geojson,.gpkg"
                  className="form-input"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <span className="form-hint">Accepted: .csv, .tif, .tiff, .geojson, .gpkg · Max 64 MB</span>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Dataset Contract (JSON)</label>
              <textarea
                id="upload-metadata"
                className="form-textarea"
                value={metaJson}
                onChange={(e) => setMetaJson(e.target.value)}
                style={{ minHeight: 280 }}
              />
              <span className="form-hint">
                Edit name, kind, provenance.status (observed/derived/assumed), units, and hydro fields.
              </span>
            </div>
            <button
              id="btn-upload-dataset"
              className="btn btn-primary"
              disabled={busy || !file || !project}
              onClick={handleUpload}
            >
              {busy ? <span className="spinner" /> : '↑'} Upload Dataset
            </button>
          </div>
        </div>
      )}

      {/* Source register table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Source Register</span>
          <span style={{ fontSize: 12, color: '#64748B' }}>{datasets.length} versioned sources</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {datasets.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📂</div>
              <div className="empty-state-title">No datasets imported</div>
              <div className="empty-state-text">
                Missing data is not interpreted as zero. Upload at least terrain, dam specs, and a hydrograph to proceed.
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name / ID</th>
                    <th>Type</th>
                    <th>Units</th>
                    <th>Evidence</th>
                    <th>Version</th>
                    <th>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d) => (
                    <tr key={d.id}>
                      <td>
                        {d.name}
                        <small><code>{d.id}</code></small>
                      </td>
                      <td>{d.kind}</td>
                      <td>{d.provenance.units}</td>
                      <td><StatusBadge value={d.provenance.status} /></td>
                      <td>v{d.version}</td>
                      <td>
                        {d.inspection.issues.length === 0 ? (
                          <span style={{ color: '#16A34A', fontSize: 12 }}>✓ Clean</span>
                        ) : (
                          <span style={{ color: '#D97706', fontSize: 12 }}>
                            ⚠ {d.inspection.issues.length}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Missing findings */}
      {(readiness?.missing.length ?? 0) > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-header">
            <span className="card-title">Missing Inputs ({readiness!.missing.length})</span>
          </div>
          <div className="card-body" style={{ padding: '0 20px' }}>
            <div className="finding-list">
              {readiness!.missing.map((f: Finding) => (
                <div key={f.code} className="finding-item">
                  <div className="finding-marker error">!</div>
                  <div>
                    <div className="finding-code">{f.code.replace(/_/g, ' ')}</div>
                    <div className="finding-message">{f.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Warnings */}
      {(readiness?.warnings.length ?? 0) > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-header">
            <span className="card-title">Warnings ({readiness!.warnings.length})</span>
          </div>
          <div className="card-body" style={{ padding: '0 20px' }}>
            <div className="finding-list">
              {readiness!.warnings.map((f: Finding) => (
                <div key={f.code} className="finding-item">
                  <div className="finding-marker warning">i</div>
                  <div>
                    <div className="finding-code">{f.code.replace(/_/g, ' ')}</div>
                    <div className="finding-message">{f.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
