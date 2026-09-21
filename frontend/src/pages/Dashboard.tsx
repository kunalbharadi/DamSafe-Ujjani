import React, { useEffect, useRef, useState } from 'react';
import { getResultWindow, getProductArea } from '../api';
import type { Map as LibreMap } from 'maplibre-gl';
import type {
  HealthStatus, NumericalRun, Project, Readiness,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { UJJANI_DAM_LNG, UJJANI_DAM_LAT } from '../components/FloodMap2D';
import type { Page } from '../types';

type DashboardProps = {
  project: Project | null;
  health: HealthStatus | null;
  readiness: Readiness | null;
  runs: NumericalRun[];
  onNavigate: (page: Page) => void;
};

function MiniMap({ bounds }: { bounds: [number, number, number, number] | null }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = ref.current;
    if (!container) return;
    let disposed = false;
    let mapInst: LibreMap | null = null;

    (async () => {
      const lib = await import('maplibre-gl');
      if (disposed || !container) return;
      const [w, s, e, n] = bounds ?? [74.6, 17.65, 75.95, 18.35];
      const instance = new lib.Map({
        container,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap',
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-opacity': 0.75 } }],
        },
        bounds: [[w, s], [e, n]],
        fitBoundsOptions: { padding: 30 },
        interactive: false,
      });
      instance.on('load', () => {
        if (disposed) return;
        instance.addSource('dam', {
          type: 'geojson',
          data: {
            type: 'Feature', properties: {},
            geometry: { type: 'Point', coordinates: [UJJANI_DAM_LNG, UJJANI_DAM_LAT] },
          },
        });
        instance.addLayer({
          id: 'dam-dot', type: 'circle', source: 'dam',
          paint: { 'circle-radius': 8, 'circle-color': '#F97316', 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
        });
        instance.addSource('domain', {
          type: 'geojson',
          data: {
            type: 'Feature', properties: {},
            geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
          },
        });
        instance.addLayer({
          id: 'domain-line', type: 'line', source: 'domain',
          paint: { 'line-color': '#F97316', 'line-width': 1.5, 'line-dasharray': [4, 3] },
        });
      });
      mapInst = instance;
    })();

    return () => { disposed = true; mapInst?.remove(); };
  }, [bounds]);

  return <div ref={ref} style={{ width: '100%', height: '100%' }} aria-label="Study area mini-map" />;
}

export function Dashboard({ project, health, readiness, runs, onNavigate }: DashboardProps) {
  const latestSucceeded = runs.find((r) => r.state === 'SUCCEEDED');
  const [summary, setSummary] = useState<{ depth: number | null; area: number; elapsed: number } | null>(null);
  const [summaryError, setSummaryError] = useState('');
  useEffect(() => {
    let cancelled = false;
    setSummary(null); setSummaryError('');
    if (!project || !latestSucceeded) return;
    (async () => {
      const window = await getResultWindow(project.id, latestSucceeded.id, 'h', 0, 1);
      const area = await getProductArea(project.id, latestSucceeded.id, 0, 1);
      if (cancelled) return;
      const frame = window.frames[0];
      const values = frame.values.filter((v, i): v is number => v !== null && frame.states[i] !== 'NODATA');
      setSummary({ depth: values.length ? Math.max(...values) : null, area: area.frames[0].flooded_area_m2, elapsed: frame.elapsed_s });
    })().catch(e => { if (!cancelled) setSummaryError(String(e)); });
    return () => { cancelled = true; };
  }, [project?.id, latestSucceeded?.id]);
  const isRunning = runs.some((r) => ['QUEUED', 'RUNNING'].includes(r.state));
  const readinessScore = readiness
    ? readiness.missing.length
    : null;

  const dflowEngine = health?.engines.find((e) => e.engine === 'dflowfm');
  const sphEngine = health?.engines.find((e) => e.engine === 'dualsphysics');

  const WORKFLOW_STEPS: { id: Page; icon: string; label: string }[] = [
    { id: 'data-setup', icon: '📊', label: 'Data' },
    { id: 'scenario-builder', icon: '⚙', label: 'Scenario' },
    { id: 'simulation', icon: '▶', label: 'Simulate' },
    { id: 'results', icon: '🌊', label: 'Analyze' },
    { id: 'validation', icon: '✓', label: 'Validate' },
    { id: 'impact', icon: '🚨', label: 'Respond' },
  ];

  return (
    <div id="page-dashboard">
      {/* Hero */}
      <div className="dashboard-hero">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h1 className="dashboard-hero-title">DamSafe</h1>
            <p className="dashboard-hero-sub">Dam Break Inundation Modelling &amp; Decision Support System</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span className="project-chip">💧 Ujjani Dam — Bhima River · Maharashtra</span>
              <span className="sih-chip">SIH PS 26161</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              id="btn-new-simulation"
              className="btn btn-primary"
              onClick={() => onNavigate('simulation')}
            >
              ▶ New Simulation
            </button>
            <button
              id="btn-open-results"
              className="btn"
              style={{ borderColor: 'rgba(255,255,255,0.15)', color: 'white', background: 'rgba(255,255,255,0.08)' }}
              onClick={() => onNavigate('results')}
              disabled={!latestSucceeded}
            >
              🌊 Open Latest Results
            </button>
          </div>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        {/* Data Readiness */}
        <div className="stat-card">
          <div className="stat-label">Data Readiness</div>
          <div className={`stat-value ${readinessScore === 0 ? 'green' : ''}`}>
            {readinessScore !== null ? `${readinessScore} gaps` : '—'}
          </div>
          <div className="stat-sub">
            {readiness
              ? `${readiness.missing.length} missing · ${readiness.warnings.length} warnings`
              : 'Run readiness audit'}
          </div>
        </div>

        {/* Latest Simulation */}
        <div className="stat-card">
          <div className="stat-label">Latest Simulation</div>
          <div className="stat-value" style={{ fontSize: 18, fontWeight: 700 }}>
            {isRunning ? (
              <span style={{ color: '#D97706' }}>Running…</span>
            ) : latestSucceeded ? (
              <StatusBadge value="SUCCEEDED" />
            ) : (
              <span style={{ color: '#64748B', fontSize: 14 }}>No run yet</span>
            )}
          </div>
          <div className="stat-sub">
            {latestSucceeded
              ? `${latestSucceeded.input.request.engine} · ${latestSucceeded.input.case_classification ?? latestSucceeded.input.request.case_kind}`
              : 'Go to Simulation to start'}
          </div>
        </div>

        {/* Validation Status */}
        <div className="stat-card">
          <div className="stat-label">Validation Status</div>
          <div className="stat-value" style={{ fontSize: 14, fontWeight: 700 }}>
            <span className="badge badge-gray">NOT VALIDATED</span>
          </div>
          <div className="stat-sub">Requires satellite comparison — see Validation</div>
        </div>

        {/* Maximum Depth */}
        <div className="stat-card blue">
          <div className="stat-label">Maximum Depth · first saved frame</div>
          <div className="stat-value">
            {summary?.depth != null ? summary.depth.toFixed(2) + ' m' : '—'}
          </div>
          <div className="stat-sub">{summary ? 'Saved solver output · T+' + summary.elapsed + ' s' : summaryError || 'Reading saved output…'}</div>
        </div>

        {/* Flooded Area */}
        <div className="stat-card blue">
          <div className="stat-label">Wet Area · first saved frame</div>
          <div className="stat-value">{summary ? (summary.area / 1e6).toFixed(2) + ' km²' : '—'}</div>
          <div className="stat-sub">Includes initial water; not newly flooded land</div>
        </div>

        {/* Affected Settlements */}
        <div className="stat-card">
          <div className="stat-label">Affected Settlements</div>
          <div className="stat-value" style={{ fontSize: 14 }}>
            <span className="badge badge-data-required">DATA REQUIRED</span>
          </div>
          <div className="stat-sub">Requires exposure evaluation</div>
        </div>
      </div>

      {/* Two column: mini-map + workflow */}
      <div className="two-col-6040" style={{ marginBottom: 24 }}>
        {/* Mini map */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Study Area</span>
            <span className="badge badge-blue">Bhima River Basin</span>
          </div>
          <div style={{ height: 280, borderRadius: '0 0 10px 10px', overflow: 'hidden' }}>
            <MiniMap bounds={project?.verified_bounds_wgs84 ?? null} />
          </div>
          <div className="card-footer">
            <span style={{ fontSize: 11, color: '#64748B' }}>
              Ujjani Dam · repository reference location · Bhima River, Maharashtra
            </span>
            <button
              className="btn btn-sm"
              style={{ float: 'right' }}
              onClick={() => onNavigate('study-area')}
            >
              Explore →
            </button>
          </div>
        </div>

        {/* Workflow + Engine status */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Workflow pipeline */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Workflow</span>
              <span style={{ fontSize: 11, color: '#64748B' }}>Click a step to navigate</span>
            </div>
            <div className="card-body" style={{ padding: '16px 12px' }}>
              <div className="workflow-pipeline">
                {WORKFLOW_STEPS.map((step, i) => (
                  <React.Fragment key={step.id}>
                    <div className="workflow-step">
                      <button
                        className="workflow-node"
                        onClick={() => onNavigate(step.id)}
                        aria-label={`Go to ${step.label}`}
                      >
                        <span className="workflow-icon">{step.icon}</span>
                        <span className="workflow-label">{step.label}</span>
                      </button>
                    </div>
                    {i < WORKFLOW_STEPS.length - 1 && (
                      <span className="workflow-arrow">→</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>

          {/* Engine status */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Solver Engines</span>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>D-Flow FM</div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>2D Regional Hydrodynamic</div>
                </div>
                {dflowEngine
                  ? <StatusBadge value={dflowEngine.available ? 'AVAILABLE' : 'UNAVAILABLE'} />
                  : <StatusBadge value="UNAVAILABLE" />}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>DualSPHysics</div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>3D Near-Field SPH</div>
                </div>
                {sphEngine
                  ? <StatusBadge value={sphEngine.available ? 'AVAILABLE' : 'UNAVAILABLE'} />
                  : <StatusBadge value="UNAVAILABLE" />}
              </div>
              <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>
                {health?.database === 'sqlite' ? '⚠ SQLite preview mode' : `Database: ${health?.database ?? '…'}`}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SIH Statement */}
      <div className="alert alert-info" style={{ fontSize: 12 }}>
        <span style={{ fontSize: 18 }}>ℹ</span>
        <div>
          <strong>SIH 2026 · Problem Statement 26161</strong> — Dam Break Inundation Modelling Using Hydrodynamic Modelling of any River.<br />
          Current demonstration: Ujjani Dam on the Bhima River, Maharashtra using D-Flow FM (2D hydrodynamic) + DualSPHysics (3D SPH near-field).
          All results are classified and must not be used as official flood predictions.
        </div>
      </div>
    </div>
  );
}
