import React, { useState } from 'react';
import type { NumericalRun, Project, ResultMetadata, Scenario } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { downloadExport } from '../api';

type ReportsExportProps = {
  project: Project | null;
  runs: NumericalRun[];
  scenarios: Scenario[];
  metadata: ResultMetadata | null;
  onError: (e: string) => void;
  onNotice: (n: string) => void;
};

const EXPORT_FORMATS = [
  { id: 'geotiff', icon: '🗺', name: 'GeoTIFF', desc: 'Raster flood depth/velocity grid. GIS-ready. Standard for hydrological mapping.' },
  { id: 'shapefile', icon: '📐', name: 'Shapefile', desc: 'Result-cell points with saved numerical attributes. Opens in ArcGIS and QGIS.' },
  { id: 'kml', icon: '📌', name: 'KML', desc: 'Google Earth / Google Maps compatible. Field teams can open on mobile.' },
  { id: 'geojson', icon: '{}', name: 'GeoJSON', desc: 'Open standard GIS vector format. Web-mapping and API compatible.' },
  { id: 'csv', icon: '📊', name: 'CSV', desc: 'Tabular cell results with coordinates. For further numerical analysis.' },
  { id: 'html', icon: '📄', name: 'HTML Report', desc: 'Interactive situation report for dashboards and briefings.' },
];

export function ReportsExport({ project, runs, scenarios, metadata, onError, onNotice }: ReportsExportProps) {
  const [selectedRunId, setSelectedRunId] = useState('');
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [showSitRep, setShowSitRep] = useState(false);

  const succeededRuns = runs.filter((r) => r.state === 'SUCCEEDED');
  const selectedRun = runs.find((r) => r.id === selectedRunId);

  async function handleExport(format: string) {
    if (!project || !selectedRunId) return;
    setExportLoading(format);
    try {
      await downloadExport(project.id, selectedRunId, format);
      onNotice(`${format.toUpperCase()} export downloaded.`);
    } catch (e) {
      onError(String(e));
    } finally {
      setExportLoading(null);
    }
  }

  const sitrep = {
    studyArea: project ? { name: project.name, siteKey: project.site_key, bounds: project.verified_bounds_wgs84 } : null,
    scenario: selectedRun
      ? scenarios.find((s) => s.id === selectedRun.input.request.scenario_id) ?? null
      : null,
    solver: selectedRun
      ? { engine: selectedRun.input.request.engine, caseKind: selectedRun.input.request.case_kind, classification: selectedRun.input.case_classification }
      : null,
    results: metadata && metadata.run_id === selectedRunId
      ? { frames: metadata.output_frame_count, cells: metadata.cell_count, elapsed: metadata.simulation_elapsed_seconds[1], crs: metadata.crs, inputMode: metadata.input_mode }
      : null,
    generatedAt: new Date().toISOString(),
  };

  return (
    <div id="page-reports">
      <div className="page-header">
        <div className="page-eyebrow">⑧ Reports &amp; Export</div>
        <h1 className="page-title">Export &amp; Situation Report</h1>
        <p className="page-subtitle">
          Download simulation results in standard GIS formats or generate a situation report.
          All exports are connected to real solver outputs — no fabricated data.
        </p>
      </div>

      {/* Run selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body" style={{ padding: 16 }}>
          <div className="form-group" style={{ marginBottom: 0, maxWidth: 460 }}>
            <label className="form-label">Select Run to Export</label>
            <select
              id="export-run-select"
              className="form-select"
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
            >
              <option value="">— Select a succeeded run —</option>
              {succeededRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id.slice(0, 16)}… · {r.input.request.engine} · {r.input.request.case_kind}
                </option>
              ))}
            </select>
            {succeededRuns.length === 0 && (
              <span className="form-hint" style={{ color: '#DC2626' }}>
                No succeeded runs. Complete a simulation first.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Export format cards */}
      <div className="export-grid" style={{ marginBottom: 24 }}>
        {EXPORT_FORMATS.map((fmt) => (
          <div key={fmt.id} className="export-card">
            <div className="export-card-icon">{fmt.icon}</div>
            <div className="export-card-name">{fmt.name}</div>
            <div className="export-card-desc">{fmt.desc}</div>
            <button
              id={`export-btn-${fmt.id}`}
              className="btn btn-outline-orange btn-sm"
              disabled={!selectedRunId || !project || exportLoading === fmt.id}
              onClick={() => handleExport(fmt.id)}
            >
              {exportLoading === fmt.id
                ? <><span className="spinner" /> Generating…</>
                : `↓ Download ${fmt.name}`}
            </button>
          </div>
        ))}
      </div>

      {/* Situation Report */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">📋 Situation Report</span>
          <button
            id="btn-generate-sitrep"
            className="btn btn-outline-orange btn-sm"
            onClick={() => setShowSitRep(!showSitRep)}
          >
            {showSitRep ? 'Hide Report' : 'Generate Situation Report'}
          </button>
        </div>
        {showSitRep && (
          <div className="card-body">
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 24 }}>
              {/* Situation Report Header */}
              <div style={{ marginBottom: 20, borderBottom: '2px solid #F97316', paddingBottom: 16 }}>
                <h2 style={{ fontSize: 20, fontWeight: 900, color: '#0F172A', letterSpacing: '-0.03em' }}>
                  DamSafe — Simulation Situation Report
                </h2>
                <p style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                  Generated: {sitrep.generatedAt} · NOT FOR OFFICIAL USE
                </p>
              </div>

              {/* Study Area */}
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>① Study Area</h3>
                {sitrep.studyArea ? (
                  <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    <div className="detail-item"><span className="detail-label">Project</span><span className="detail-value">{sitrep.studyArea.name}</span></div>
                    <div className="detail-item"><span className="detail-label">Site Key</span><span className="detail-value"><code>{sitrep.studyArea.siteKey}</code></span></div>
                    <div className="detail-item">
                      <span className="detail-label">Domain Bounds</span>
                      <span className="detail-value" style={{ fontSize: 11 }}>
                        {sitrep.studyArea.bounds
                          ? `${sitrep.studyArea.bounds[0].toFixed(2)}°E–${sitrep.studyArea.bounds[2].toFixed(2)}°E, ${sitrep.studyArea.bounds[1].toFixed(2)}°N–${sitrep.studyArea.bounds[3].toFixed(2)}°N`
                          : 'Not verified'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: '#64748B' }}>No project selected.</p>
                )}
              </section>

              {/* Scenario */}
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>② Scenario</h3>
                {sitrep.scenario ? (
                  <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    <div className="detail-item"><span className="detail-label">Name</span><span className="detail-value">{sitrep.scenario.name}</span></div>
                    <div className="detail-item">
                      <span className="detail-label">Input Mode</span>
                      <span className="detail-value"><StatusBadge value={sitrep.scenario.snapshot.input_mode} /></span>
                    </div>
                    <div className="detail-item"><span className="detail-label">Forcing</span><span className="detail-value">{sitrep.scenario.snapshot.scenario?.forcing?.mode ?? '—'}</span></div>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: '#64748B' }}>
                    {selectedRun ? 'No scenario linked to this run.' : 'No run selected.'}
                  </p>
                )}
              </section>

              {/* Solver */}
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>③ Solver</h3>
                {sitrep.solver ? (
                  <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
                    <div className="detail-item"><span className="detail-label">Engine</span><span className="detail-value"><code>{sitrep.solver.engine}</code></span></div>
                    <div className="detail-item"><span className="detail-label">Case Kind</span><span className="detail-value">{sitrep.solver.caseKind}</span></div>
                    <div className="detail-item">
                      <span className="detail-label">Classification</span>
                      <span className="detail-value">
                        {sitrep.solver.classification ? <StatusBadge value={sitrep.solver.classification} /> : '—'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: '#64748B' }}>No run selected.</p>
                )}
              </section>

              {/* Results */}
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>④ Simulation Results</h3>
                {sitrep.results ? (
                  <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
                    <div className="detail-item"><span className="detail-label">Frames</span><span className="detail-value">{sitrep.results.frames}</span></div>
                    <div className="detail-item"><span className="detail-label">Cells</span><span className="detail-value">{sitrep.results.cells}</span></div>
                    <div className="detail-item"><span className="detail-label">Elapsed (s)</span><span className="detail-value">{sitrep.results.elapsed}</span></div>
                    <div className="detail-item"><span className="detail-label">CRS</span><span className="detail-value"><code>{sitrep.results.crs ?? '—'}</code></span></div>
                    <div className="detail-item">
                      <span className="detail-label">Input Mode</span>
                      <span className="detail-value"><StatusBadge value={sitrep.results.inputMode} /></span>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: '#64748B' }}>Results metadata not loaded. Go to Results tab first.</p>
                )}
              </section>

              {/* Validation */}
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>⑤ Validation Status</h3>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <StatusBadge value="NOT VALIDATED" />
                  <span style={{ fontSize: 12, color: '#64748B' }}>
                    Satellite agreement not computed. See Validation page.
                  </span>
                </div>
              </section>

              {/* Limitations */}
              <section>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F97316', marginBottom: 8 }}>⑥ Limitations &amp; Disclaimers</h3>
                <div className="alert alert-warning" style={{ fontSize: 12, marginBottom: 8 }}>
                  ⚠ This report is generated from a <strong>demonstration / laboratory simulation</strong>.
                  It does not represent a validated flood prediction and must not be used for
                  emergency planning or official communication without independent professional review.
                </div>
                <ul style={{ fontSize: 12, color: '#64748B', lineHeight: 1.8, paddingLeft: 16 }}>
                  <li>Breach parameters are hypothetical unless specified as OBSERVED</li>
                  <li>Terrain is assumed SRTM unless a verified DEM dataset was uploaded</li>
                  <li>Channel geometry is parameterised, not surveyed cross-sections</li>
                  <li>Satellite validation was not completed at time of report generation</li>
                  <li>Population, monetary and evacuation estimates are not provided (DATA REQUIRED)</li>
                  <li>SIH PS 26161 — prototype system, not production-cleared</li>
                </ul>
              </section>
            </div>

            <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
              <button
                id="btn-copy-sitrep"
                className="btn btn-outline-orange"
                onClick={() => {
                  const el = document.querySelector('#page-reports .card-body > div');
                  if (el) navigator.clipboard?.writeText(el.textContent ?? '');
                }}
              >
                📋 Copy to Clipboard
              </button>
              <span className="caption" style={{ alignSelf: 'center' }}>
                Report contains only real data from the backend. No fabricated values.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
