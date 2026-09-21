import React, { useEffect, useState } from 'react';
import type { Engine, HealthStatus, NumericalRun, Project, Scenario } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { cancelRun, submitRun } from '../api';

type SimulationProps = {
  project: Project | null;
  health: HealthStatus | null;
  runs: NumericalRun[];
  scenarios?: Scenario[];
  onRefresh: () => void;
  onError: (e: string) => void;
  onNotice: (n: string) => void;
  onLoadResults: (runId: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
};

function EngineCard({ engine, onRun, busy, projectSynthetic, onRunSiteScenario, hasScenario }: {
  engine: Engine;
  onRun: () => void;
  busy: boolean;
  projectSynthetic: boolean;
  onRunSiteScenario?: () => void;
  hasScenario?: boolean;
}) {
  const isDflow = engine.engine === 'dflowfm';
  return (
    <div className={`engine-card ${engine.available ? 'engine-available' : 'engine-unavailable'}`}>
      <div className="engine-card-header">
        <div>
          <div className="engine-card-title">
            {isDflow ? 'D-Flow FM' : 'DualSPHysics'}
          </div>
          <div className="engine-card-subtitle">
            {isDflow
              ? '2D regional hydrodynamic model — Delft3D Flexible Mesh SWE solver'
              : '3D near-field particle model — Lagrangian SPH (not full-river)'}
          </div>
        </div>
        <StatusBadge value={engine.available ? 'AVAILABLE' : 'UNAVAILABLE'} />
      </div>
      <div className="engine-card-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* Engine scope note */}
          <div className="alert alert-info" style={{ marginBottom: 0, fontSize: 11 }}>
            {isDflow
              ? '🗺 Models the downstream river reach as a 2D shallow-water domain. Use for inundation extent, depth, velocity, and arrival time.'
              : '💧 Models the near-field dam-breach zone in 3D particle detail. Does NOT model the full river — SPH is complementary to D-Flow FM.'}
          </div>

          <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr', margin: '8px 0' }}>
            <div className="detail-item">
              <span className="detail-label">Engine ID</span>
              <span className="detail-value"><code>{engine.engine}</code></span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Status</span>
              <span className="detail-value">
                {engine.available ? engine.image_id ?? 'Ready' : engine.reason ?? 'Unavailable'}
              </span>
            </div>
          </div>

          {engine.available ? (
            <>
              {projectSynthetic ? (
                <>
                  <div className="alert alert-warning" style={{ fontSize: 11, marginBottom: 0 }}>
                    Official laboratory benchmark example for synthetic validation.
                  </div>
                  <button
                    id={`btn-run-${engine.engine}`}
                    className="btn btn-primary"
                    disabled={busy}
                    onClick={onRun}
                  >
                    {busy ? <span className="spinner" /> : '▶'} Run Official Laboratory Example
                  </button>
                </>
              ) : isDflow ? (
                <>
                  <div className="alert alert-success" style={{ fontSize: 11, marginBottom: 0 }}>
                    ✓ Ready for site scenario execution. Select a saved scenario above.
                  </div>
                  <button
                    id={`btn-run-${engine.engine}`}
                    className="btn btn-primary"
                    disabled={busy || !hasScenario}
                    onClick={onRunSiteScenario}
                    title={!hasScenario ? 'Select or save a scenario first' : undefined}
                  >
                    {busy ? <span className="spinner" /> : '▶'} Run D-Flow FM Site Simulation
                  </button>
                </>
              ) : (
                <>
                  <div className="alert alert-info" style={{ fontSize: 11, marginBottom: 0 }}>
                    DualSPHysics near-field particle simulation. Runs laboratory benchmarks or near-field breach blocks.
                  </div>
                  <button
                    id={`btn-run-${engine.engine}`}
                    className="btn btn-outline-blue"
                    disabled={busy}
                    onClick={onRun}
                  >
                    {busy ? <span className="spinner" /> : '▶'} Run Near-Field Benchmark
                  </button>
                </>
              )}
            </>
          ) : (
            <p className="caption" style={{ color: '#DC2626' }}>
              Engine unavailable: {engine.reason ?? 'Docker image not found. Verify setup.'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function progressLabel(run: NumericalRun): string {
  const p = run.result.progress;
  if (!p) return '';
  if (p.frame != null && p.frames_total) return `frame ${p.frame}/${p.frames_total}`;
  if (p.elapsed_seconds != null) return `${p.elapsed_seconds.toFixed(1)} s elapsed`;
  if (p.stage) return p.stage;
  return 'running…';
}

export function Simulation({
  project, health, runs, scenarios = [], onRefresh, onError, onNotice, onLoadResults, busy, setBusy,
}: SimulationProps) {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');

  useEffect(() => {
    if (scenarios.length > 0 && !selectedScenarioId) {
      setSelectedScenarioId(scenarios[0].id);
    }
  }, [scenarios, selectedScenarioId]);

  async function handleRun(engine: 'dualsphysics' | 'dflowfm') {
    if (!project) return;
    setBusy(true);
    try {
      await submitRun(project.id, {
        engine,
        case_kind: 'OFFICIAL_EXAMPLE',
        idempotency_key: crypto.randomUUID().replace(/-/g, ''),
      });
      await onRefresh();
      onNotice(`${engine} laboratory example queued. Execution success is separate from scientific validation.`);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleRunSiteScenario() {
    if (!project || !selectedScenarioId) return;
    setBusy(true);
    try {
      await submitRun(project.id, {
        engine: 'dflowfm',
        case_kind: 'SITE_SCENARIO',
        scenario_id: selectedScenarioId,
        idempotency_key: crypto.randomUUID().replace(/-/g, ''),
      });
      await onRefresh();
      onNotice('Site scenario queued for D-Flow FM 2D hydrodynamic simulation.');
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel(runId: string) {
    if (!project) return;
    setBusy(true);
    try {
      await cancelRun(project.id, runId);
      await onRefresh();
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const dflowEngine = health?.engines.find((e) => e.engine === 'dflowfm');
  const sphEngine = health?.engines.find((e) => e.engine === 'dualsphysics');
  const isProjectSynthetic = project?.synthetic ?? false;

  return (
    <div id="page-simulation">
      <div className="page-header">
        <div className="page-eyebrow">④ Simulation</div>
        <h1 className="page-title">Run Hydrodynamic Solvers</h1>
        <p className="page-subtitle">
          Two separate solvers — D-Flow FM (2D regional) and DualSPHysics (3D near-field).
          Each addresses a different physical scale. DualSPHysics does not model the full river.
        </p>
      </div>

      {/* Site Project Scenario Runner */}
      {project && !isProjectSynthetic && (
        <div className="card" style={{ marginBottom: 20, border: '1px solid #CBD5E1' }}>
          <div className="card-header" style={{ background: '#F8FAFC' }}>
            <span className="card-title">Run Site Scenario (D-Flow FM 2D)</span>
            <span className="badge badge-orange">{project.name}</span>
          </div>
          <div className="card-body">
            <p style={{ fontSize: 13, color: '#475569', marginBottom: 12 }}>
              Execute 2D shallow-water flood wave propagation along the river reach downstream using Delft3D Flexible Mesh.
            </p>
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 280 }}>
                <label className="detail-label" style={{ display: 'block', marginBottom: 6 }}>
                  Select Saved Scenario Snapshot:
                </label>
                <select
                  id="select-site-scenario"
                  className="form-control"
                  style={{ width: '100%', padding: '8px 12px' }}
                  value={selectedScenarioId}
                  onChange={(e) => setSelectedScenarioId(e.target.value)}
                >
                  {scenarios.length === 0 && (
                    <option value="">No saved scenarios available. Create one in Scenario Builder.</option>
                  )}
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id.slice(0, 8)}…)
                    </option>
                  ))}
                </select>
              </div>
              <button
                id="btn-run-site-scenario"
                className="btn btn-primary"
                disabled={busy || !selectedScenarioId || !dflowEngine?.available}
                onClick={handleRunSiteScenario}
              >
                {busy ? <span className="spinner" /> : '▶'} Run D-Flow FM Simulation
              </button>
            </div>
            {scenarios.length === 0 && (
              <p className="caption" style={{ marginTop: 8, color: '#D97706' }}>
                💡 Go to <strong>Scenario Builder</strong> to configure and save a dam breach or controlled release scenario first.
              </p>
            )}
          </div>
        </div>
      )}

      {project?.synthetic && (
        <div className="alert alert-synthetic" style={{ marginBottom: 20 }}>
          <strong>SYNTHETIC EXAMPLE</strong> — these inputs do not represent Ujjani and cannot be used as a site prediction.
        </div>
      )}

      {/* Engine cards */}
      <div className="engine-grid">
        {dflowEngine && (
          <EngineCard
            engine={dflowEngine}
            onRun={() => handleRun('dflowfm')}
            busy={busy}
            projectSynthetic={isProjectSynthetic}
            onRunSiteScenario={handleRunSiteScenario}
            hasScenario={Boolean(selectedScenarioId)}
          />
        )}
        {sphEngine && (
          <EngineCard
            engine={sphEngine}
            onRun={() => handleRun('dualsphysics')}
            busy={busy}
            projectSynthetic={isProjectSynthetic}
          />
        )}
        {!dflowEngine && !sphEngine && (
          <div className="alert alert-warning">No engine information available — check /api/health</div>
        )}
      </div>

      {/* Run history */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Run History</span>
          <span style={{ fontSize: 12, color: '#64748B' }}>{runs.length} runs</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {runs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">▶</div>
              <div className="empty-state-title">No simulation runs</div>
              <div className="empty-state-text">Submit a laboratory example to start.</div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Engine</th>
                    <th>Case / Classification</th>
                    <th>State / Progress</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <code style={{ fontSize: 11 }}>{run.id.slice(0, 14)}…</code>
                        <small>{run.input.request.engine}</small>
                      </td>
                      <td>
                        <span className="badge badge-blue">{run.input.request.engine}</span>
                      </td>
                      <td>
                        <strong style={{ fontSize: 12 }}>{run.input.request.case_kind}</strong>
                        {run.input.case_classification && (
                          <small style={{ color: '#D97706' }}>{run.input.case_classification}</small>
                        )}
                        {run.input.evidence_status && (
                          <small><StatusBadge value={run.input.evidence_status} /></small>
                        )}
                      </td>
                      <td>
                        <StatusBadge value={run.state} />
                        {run.result.progress && (
                          <small>{progressLabel(run)}</small>
                        )}
                        {run.result.normalization && (
                          <small>
                            {run.result.normalization.frames} frames · {run.result.normalization.cells} cells
                          </small>
                        )}
                        {run.result.error && (
                          <small style={{ color: '#DC2626' }}>{run.result.error}</small>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {['QUEUED', 'RUNNING'].includes(run.state) && (
                            <button
                              id={`btn-cancel-${run.id.slice(0, 8)}`}
                              className="btn btn-sm btn-danger"
                              onClick={() => handleCancel(run.id)}
                              disabled={busy}
                            >
                              ✕ Cancel
                            </button>
                          )}
                          {run.state === 'SUCCEEDED' && (
                            <button
                              id={`btn-load-${run.id.slice(0, 8)}`}
                              className="btn btn-sm btn-outline-orange"
                              onClick={() => onLoadResults(run.id)}
                            >
                              🌊 View Results
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
