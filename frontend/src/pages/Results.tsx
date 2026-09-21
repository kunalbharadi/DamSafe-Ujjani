import React, { useEffect, useMemo, useState } from 'react';
import type {
  LocationSeries, NumericalRun, ProductArea,
  Project, ResultFrame, ResultMetadata, ResultWindow,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { FloodMap2D } from '../components/FloodMap2D';
import { Sph3DViewer } from '../Sph3DViewer';
import { River3DViewer } from '../River3DViewer';
import { compareRuns, downloadExport, getResultWindow } from '../api';

type ResultSubTab = '2d' | 'terrain3d' | 'sph3d' | 'compare';

type ResultsProps = {
  project: Project | null;
  run: NumericalRun | null;
  metadata: ResultMetadata | null;
  raw: ResultWindow | null;
  area: ProductArea | null;
  location: LocationSeries | null;
  currentFrame: number;
  onFrameChange: (f: number) => void;
  field: 'h' | 'velocity_magnitude';
  onFieldChange: (f: 'h' | 'velocity_magnitude') => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onLoad: (runId?: string) => void;
  onExport: (format: string) => void;
  sphRunId: string;
  availableSphRuns: string[];
  onSphRunChange: (id: string) => void;
  runs: NumericalRun[];
  onError: (e: string) => void;
  onNotice: (n: string) => void;
};

const ALL_CELLS = '-1000000000,-1000000000,1000000000,1000000000';

export function Results({
  project, run, metadata, raw, area, location,
  currentFrame, onFrameChange, field, onFieldChange,
  isPlaying, onTogglePlay, onLoad, onExport,
  sphRunId, availableSphRuns, onSphRunChange,
  runs, onError, onNotice,
}: ResultsProps) {
  const [subTab, setSubTab] = useState<ResultSubTab>('2d');
  const [otherRunId, setOtherRunId] = useState('');
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null);
  const [compBusy, setCompBusy] = useState(false);

  const frameData: ResultFrame | null = useMemo(() => {
    if (!raw) return null;
    if (raw.field !== field) return null;
    return raw.frames.find((f) => f.frame === currentFrame) ?? null;
  }, [raw, currentFrame, field]);

  const maxVal = useMemo(() => {
    if (!frameData) return 0;
    return frameData.values.reduce((m: number, v) => v != null && v > m ? v : m, 0);
  }, [frameData]);

  const wetCount = useMemo(() => {
    if (!frameData) return 0;
    return frameData.states.filter((s) => s === 'WET').length;
  }, [frameData]);

  const isSiteApprox = metadata?.case_kind === 'SITE_SCENARIO' ||
    run?.input.case_classification === 'UJJANI_APPROXIMATE_DEMONSTRATION';

  async function handleCompare() {
    if (!project || !run || !otherRunId) return;
    setCompBusy(true);
    try {
      const result = await compareRuns(project.id, run.id, otherRunId);
      setComparison(result);
    } catch (e) {
      onError(String(e));
    } finally {
      setCompBusy(false);
    }
  }

  const SUB_TABS: { id: ResultSubTab; label: string; icon: string }[] = [
    { id: '2d', label: '2D Regional Flood', icon: '🗺' },
    { id: 'terrain3d', label: '3D River Mesh', icon: '🏔' },
    { id: 'sph3d', label: '3D SPH Near-Field', icon: '💧' },
    { id: 'compare', label: 'Compare', icon: '⚖' },
  ];

  return (
    <div id="page-results">
      <div className="page-header">
        <div className="page-eyebrow">⑤ Results</div>
        <h1 className="page-title">Simulation Results</h1>
        <p className="page-subtitle">
          Geographic saved cells, 3D cell visualization, DualSPHysics particle output, and run comparison.
        </p>
      </div>

      {/* Sub-tab bar */}
      <label className="form-label">Saved numerical run
        <select className="form-select" aria-label="Saved numerical run" value={run?.id ?? ''} onChange={e => onLoad(e.target.value)}>
          <option value="" disabled>Select a successful run</option>
          {runs.filter(r => r.state === 'SUCCEEDED').map(r => <option key={r.id} value={r.id}>{r.input.request.engine} · {r.id.slice(0, 12)} · {r.result.normalization?.frames ?? '?'} frames</option>)}
        </select>
      </label>
      <div className="tabs-bar">
        {SUB_TABS.map((t) => (
          <button
            key={t.id}
            id={`results-tab-${t.id}`}
            className={`tab-btn${subTab === t.id ? ' active' : ''}`}
            onClick={() => { setSubTab(t.id); if (t.id === 'terrain3d') onFieldChange('h'); }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── 2D Regional Flood ── */}
      {subTab === '2d' && (
        <TwoDFlood
          project={project}
          run={run}
          metadata={metadata}
          raw={raw}
          area={area}
          location={location}
          currentFrame={currentFrame}
          onFrameChange={onFrameChange}
          field={field}
          onFieldChange={onFieldChange}
          isPlaying={isPlaying}
          onTogglePlay={onTogglePlay}
          onLoad={() => onLoad()}
          onExport={onExport}
          frameData={frameData}
          maxVal={maxVal}
          wetCount={wetCount}
          isSiteApprox={isSiteApprox}
        />
      )}

      {/* ── 3D Terrain Flood ── */}
      {subTab === 'terrain3d' && (
        <TerrainFlood
          run={run}
          metadata={metadata}
          raw={raw}
          currentFrame={currentFrame}
          onFrameChange={onFrameChange}
          isPlaying={isPlaying}
          onTogglePlay={onTogglePlay}
          onLoad={() => onLoad()}
          field={field}
        />
      )}

      {/* ── 3D SPH Near-Field ── */}
      {subTab === 'sph3d' && (
        <SphNearField
          sphRunId={sphRunId}
          availableSphRuns={availableSphRuns}
          onSphRunChange={onSphRunChange}
        />
      )}

      {/* ── Compare ── */}
      {subTab === 'compare' && (
        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header"><span className="card-title">Run Comparison</span></div>
            <div className="card-body">
              <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
                Comparison is enabled for compatible saved outputs only. Scales are fixed to the shared contract —
                runs are never stretched independently.
              </p>
              <div className="form-row" style={{ maxWidth: 600 }}>
                <div className="form-group">
                  <label className="form-label">Run A (primary)</label>
                  <select className="form-select" value={run?.id ?? ''} disabled>
                    {run
                      ? <option value={run.id}>{run.id.slice(0, 14)}… · {run.input.request.engine}</option>
                      : <option value="">Select a run from Simulation first</option>}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Run B</label>
                  <select
                    id="compare-run-b"
                    className="form-select"
                    value={otherRunId}
                    onChange={(e) => setOtherRunId(e.target.value)}
                  >
                    <option value="">— Select run —</option>
                    {runs.filter((r) => r.state === 'SUCCEEDED' && r.id !== run?.id).map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.id.slice(0, 14)}… · {r.input.request.engine}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                id="btn-compare-runs"
                className="btn btn-primary"
                disabled={compBusy || !run || !otherRunId}
                onClick={handleCompare}
              >
                {compBusy ? <span className="spinner" /> : '⚖'} Compare Outputs
              </button>
            </div>
          </div>
          {comparison && (
            <div className="card">
              <div className="card-header"><span className="card-title">Comparison Results</span></div>
              <div className="card-body">
                <StatusBadge value={String(comparison.state ?? 'UNAVAILABLE')} />
                {comparison.state === 'COMPARABLE' ? <>
                  <p className="caption">Agreement between matching saved cells and frames; not measured real-world accuracy.</p>
                  <div className="metric-grid">
                    {[
                      ['Depth RMSE', 'depth_rmse_m', 'm'],
                      ['Velocity RMSE', 'velocity_magnitude_rmse_m_s', 'm/s'],
                      ['Extent IoU', 'mean_extent_iou', ''],
                      ['Arrival difference', 'mean_abs_arrival_difference_s', 's'],
                    ].map(([label, key, unit]) => <div className="metric-card" key={key}>{label}<strong>{typeof comparison[key] === 'number' ? Number(comparison[key]).toFixed(3) + ' ' + unit : 'Unavailable'}</strong></div>)}
                  </div>
                </> : <p>{Array.isArray(comparison.reasons) ? comparison.reasons.join('; ') : 'No compatible comparison available.'}</p>}
                <details><summary>Full comparison evidence</summary><pre className="json-pre">{JSON.stringify(comparison, null, 2)}</pre></details>
              </div>
            </div>
          )}
          {!comparison && (
            <div className="empty-state">
              <div className="empty-state-text">
                Select two successful runs and press Compare. Incompatible CRS, datum, domain, resolution,
                or thresholds will be reported rather than forced into a chart.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 2D Flood Sub-component ────────────────────────────────────────────────────
function TwoDFlood({
  project, run, metadata, raw, area, location,
  currentFrame, onFrameChange, field, onFieldChange,
  isPlaying, onTogglePlay, onLoad, onExport,
  frameData, maxVal, wetCount, isSiteApprox,
}: {
  project: Project | null;
  run: NumericalRun | null;
  metadata: ResultMetadata | null;
  raw: ResultWindow | null;
  area: ProductArea | null;
  location: LocationSeries | null;
  currentFrame: number;
  onFrameChange: (f: number) => void;
  field: 'h' | 'velocity_magnitude';
  onFieldChange: (f: 'h' | 'velocity_magnitude') => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onLoad: () => void;
  onExport: (format: string) => void;
  frameData: ResultFrame | null;
  maxVal: number;
  wetCount: number;
  isSiteApprox: boolean;
}) {
  if (!run || run.state !== 'SUCCEEDED') {
    return (
      <div className="card">
        <div className="card-body">
          <div className="empty-state">
            <div className="empty-state-icon">🌊</div>
            <div className="empty-state-title">No successful run selected</div>
            <div className="empty-state-text">
              Go to Simulation, run a D-Flow FM example, then return here and click Load Results.
            </div>
            <button className="btn btn-outline-orange" style={{ marginTop: 16 }} onClick={onLoad}>
              Load Latest Results
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!metadata || !raw || !area) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: 32 }}>
          <p style={{ marginBottom: 16, fontSize: 13 }}>Results not yet loaded for this run.</p>
          <button id="btn-load-results-2d" className="btn btn-primary" onClick={onLoad}>
            🌊 Load Numerical Results
          </button>
          <p className="caption" style={{ marginTop: 8 }}>
            Only genuine saved solver frames are rendered; there is no synthetic UI fallback.
          </p>
        </div>
      </div>
    );
  }

  const elapsed = frameData ? `${(frameData.elapsed_s / 3600).toFixed(1)} h` : '—';

  return (
    <div>
      {/* Classification banner */}
      {isSiteApprox && (
        <div className="alert alert-warning" style={{ marginBottom: 16 }}>
          <span>⚠</span>
          <div>
            <strong>{metadata.input_mode ?? 'MIXED_ASSUMPTIONS'} · {metadata.case_kind}</strong>
            — {metadata.engine} output. Source run: <code>{metadata.source_run_id.slice(0, 14)}…</code>
            {metadata.cached && ' · Cache hit (identical configuration)'}
            <br />
            <span className="badge badge-amber" style={{ marginRight: 6, marginTop: 6 }}>UJJANI APPROXIMATE DEMONSTRATION</span>
            <span className="badge badge-gray" style={{ marginRight: 6 }}>NOT VALIDATED</span>
            <span className="badge badge-gray">APPROXIMATE CHANNEL GEOMETRY</span>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 20 }}>
        <div className="stat-card blue">
          <div className="stat-label">
            {field === 'h' ? 'MAX DEPTH (FRAME)' : 'MAX VELOCITY (FRAME)'}
          </div>
          <div className="stat-value">
            {maxVal > 0
              ? field === 'h'
                ? `${maxVal.toFixed(2)} m`
                : `${maxVal.toFixed(2)} m/s`
              : '—'}
          </div>
          <div className="stat-sub">
            Frame {frameData?.frame ?? '—'} · {elapsed} elapsed
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">WET CELLS</div>
          <div className="stat-value">{wetCount}</div>
          <div className="stat-sub">of {raw.cells.length} total · Dry and NODATA excluded</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">SIMULATION ELAPSED</div>
          <div className="stat-value" style={{ fontSize: 20 }}>
            {metadata.simulation_elapsed_seconds[1]} s
          </div>
          <div className="stat-sub">
            {metadata.start_time ? `UTC start: ${metadata.start_time}` : 'UTC start unavailable'}
          </div>
        </div>
      </div>

      {/* Timeline controls */}
      <div className="timeline-bar">
        <div className="field-toggle">
          <button
            id="field-btn-depth"
            className={`field-btn${field === 'h' ? ' active' : ''}`}
            onClick={() => onFieldChange('h')}
          >
            🌊 Depth (m)
          </button>
          <button
            id="field-btn-velocity"
            className={`field-btn${field === 'velocity_magnitude' ? ' active' : ''}`}
            onClick={() => onFieldChange('velocity_magnitude')}
          >
            ⚡ Velocity (m/s)
          </button>
        </div>
        <button
          id="btn-play-pause"
          className="timeline-btn"
          onClick={onTogglePlay}
          disabled={metadata.output_frame_count <= 1}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>
        <button
          className="timeline-btn"
          disabled={currentFrame <= 0}
          onClick={() => onFrameChange(Math.max(0, currentFrame - 1))}
        >
          ⏮ −1
        </button>
        <input
          id="results-timeline-slider"
          type="range"
          className="timeline-slider"
          min={0}
          max={metadata.output_frame_count - 1}
          value={currentFrame}
          onChange={(e) => onFrameChange(Number(e.target.value))}
        />
        <button
          className="timeline-btn"
          disabled={currentFrame >= metadata.output_frame_count - 1}
          onClick={() => onFrameChange(Math.min(metadata.output_frame_count - 1, currentFrame + 1))}
        >
          +1 ⏭
        </button>
        <span className="timeline-time">
          Frame {frameData?.frame ?? '—'} / {metadata.output_frame_count - 1} · {elapsed}
        </span>
      </div>

      {/* Geographic flood map */}
      <div style={{ marginBottom: 20 }}>
        <FloodMap2D
          bounds={project?.verified_bounds_wgs84 ?? null}
          cells={raw.cells}
          frame={frameData}
          field={field}
          crs={metadata.crs}
          showDamMarker
        />
        <p className="caption">
          D-Flow FM saved frames — cells at real geographic coordinates (EPSG:32643 → WGS84).
          Background: OpenStreetMap. WET / DRY / NODATA are semantically distinct.
          The map shows actual solver cell positions, not an interpolated flood surface.
        </p>
      </div>

      {/* Derived products */}
      {area && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><span className="card-title">Derived Products</span></div>
          <div className="card-body">
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Wet Area (frame {currentFrame})</span>
                <span className="detail-value">
                  {area.frames.find(f => f.frame === currentFrame) ? `${(area.frames.find(f => f.frame === currentFrame)!.flooded_area_m2 / 1e6).toFixed(3)} km²` : '—'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Unknown Area (frame {currentFrame})</span>
                <span className="detail-value">
                  {area.frames.find(f => f.frame === currentFrame) ? `${(area.frames.find(f => f.frame === currentFrame)!.unknown_area_m2 / 1e6).toFixed(3)} km²` : '—'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Arrival Time (nearest cell)</span>
                <span className="detail-value">
                  {location?.arrival_elapsed_s == null
                    ? 'Not reached / unavailable'
                    : `${(location.arrival_elapsed_s / 3600).toFixed(1)} h`}
                </span>
              </div>
            </div>
            <p className="caption">
              {area.area_semantics} · baseline: {area.baseline_water} ·
              threshold: {area.threshold_m} m · Duration uses saved frames, not interpolated values.
            </p>
          </div>
        </div>
      )}

      {/* Technical metadata + exports */}
      <div className="card">
        <div className="card-header"><span className="card-title">Provenance &amp; Technical Details</span></div>
        <div className="card-body">
          <div className="detail-grid">
            <div className="detail-item"><span className="detail-label">CRS</span><span className="detail-value"><code>{metadata.crs ?? 'Unknown'}</code></span></div>
            <div className="detail-item"><span className="detail-label">Vertical Datum</span><span className="detail-value">{metadata.vertical_datum ?? 'Unknown'}</span></div>
            <div className="detail-item"><span className="detail-label">Units (h / velocity)</span><span className="detail-value"><code>{metadata.units.h ?? '—'} / {metadata.units.u ?? '—'}</code></span></div>
            <div className="detail-item"><span className="detail-label">Nodata Encoding</span><span className="detail-value">{metadata.nodata_encoding}</span></div>
            <div className="detail-item"><span className="detail-label">Frames / Cells</span><span className="detail-value">{metadata.output_frame_count} / {metadata.cell_count}</span></div>
            <div className="detail-item"><span className="detail-label">Arrival Precision</span><span className="detail-value">{metadata.arrival_precision}</span></div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
            {['geotiff', 'kml', 'geojson', 'shapefile', 'csv', 'html'].map((fmt) => (
              <button
                key={fmt}
                id={`export-${fmt}`}
                className="btn btn-sm"
                onClick={() => onExport(fmt)}
              >
                ↓ {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── 3D Terrain Flood Sub-component ───────────────────────────────────────────
function TerrainFlood({
  run, metadata, raw, currentFrame, onFrameChange, isPlaying, onTogglePlay, onLoad, field,
}: {
  run: NumericalRun | null;
  metadata: ResultMetadata | null;
  raw: ResultWindow | null;
  currentFrame: number;
  onFrameChange: (f: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onLoad: () => void;
  field: 'h' | 'velocity_magnitude';
}) {
  // Check for CesiumJS token in env
  const cesiumToken = null; // Terrain integration is not installed; credentials alone cannot enable it.

  if (!cesiumToken) {
    return (
      <div>
        <div className="alert alert-info" style={{ marginBottom: 20 }}>
          <span>ℹ</span>
          <div>
            <strong>Saved river mesh in 3D</strong> — Native face boundaries, cell bed elevation and saved water depth.
            Use the 2D tab for geographic context. Surrounding terrain imagery is not included in these solver files.
          </div>
        </div>

        {/* Fall back to River3DViewer */}
        {(!run || run.state !== 'SUCCEEDED' || !metadata || !raw) ? (
          <div className="card">
            <div className="card-body" style={{ textAlign: 'center' }}>
              <p style={{ marginBottom: 16, fontSize: 13 }}>Load D-Flow results to see approximate 3D cell visualization.</p>
              <button className="btn btn-outline-orange" onClick={onLoad}>Load Results</button>
            </div>
          </div>
        ) : (
          <div>
            <div className="alert alert-warning">
              Saved D-Flow water surface over the original computational faces. Inputs remain an approximate site demonstration.
            </div>
            <div className="timeline-bar" style={{ marginBottom: 12 }}>
              <button className="timeline-btn" onClick={onTogglePlay}>
                {isPlaying ? '⏸ Pause' : '▶ Play'}
              </button>
              <input
                type="range"
                className="timeline-slider"
                min={0}
                max={metadata.output_frame_count - 1}
                value={currentFrame}
                onChange={(e) => onFrameChange(Number(e.target.value))}
              />
              <span className="timeline-time">Frame {currentFrame} / {metadata.output_frame_count - 1}</span>
            </div>
            <River3DViewer
              cells={raw.cells}
              frame={field === 'h' ? raw.frames.find((f) => f.frame === currentFrame) : undefined}
              frameNumber={currentFrame}
              crs={metadata.crs}
            />
          </div>
        )}
      </div>
    );
  }

  // Token available — placeholder for CesiumJS integration
  return (
    <div className="card">
      <div className="card-body">
        <div className="empty-state">
          <div className="empty-state-icon">🏔</div>
          <div className="empty-state-title">CesiumJS 3D Terrain</div>
          <div className="empty-state-text">
            Token detected. Full CesiumJS terrain integration coming in next phase.
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── 3D SPH Near-Field Sub-component ──────────────────────────────────────────
function SphNearField({
  sphRunId, availableSphRuns, onSphRunChange,
}: {
  sphRunId: string;
  availableSphRuns: string[];
  onSphRunChange: (id: string) => void;
}) {
  return (
    <div>
      <div className="alert alert-info" style={{ marginBottom: 16 }}>
        <span>💧</span>
        <div>
          <strong>DualSPHysics 3D Near-Field Output</strong> — Lagrangian particle simulation of the dam-breach
          near-field zone. This does NOT represent the full river. Particles are loaded from real solver output.
          Do not confuse with D-Flow FM regional results.
        </div>
      </div>

      {/* Run selector */}
      {availableSphRuns.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-body" style={{ padding: 16 }}>
            <div className="form-group" style={{ marginBottom: 0, maxWidth: 460 }}>
              <label className="form-label">SPH Run</label>
              <select
                id="sph-run-selector"
                className="form-select"
                value={sphRunId}
                onChange={(e) => onSphRunChange(e.target.value)}
              >
                {availableSphRuns.map((id) => (
                  <option key={id} value={id}>{id}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      <Sph3DViewer
        runId={sphRunId}
      />
    </div>
  );
}
