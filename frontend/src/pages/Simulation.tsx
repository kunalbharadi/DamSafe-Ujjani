import React, { useState } from 'react';
import type { Engine, HealthStatus, NumericalRun, Project } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { cancelRun, submitRun } from '../api';

type SimulationProps = {
  project: Project | null;
  health: HealthStatus | null;
  runs: NumericalRun[];
  onRefresh: () => void;
  onError: (e: string) => void;
  onNotice: (n: string) => void;
  onLoadResults: (runId: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
};

function EngineCard({ engine, onRun, busy, projectSynthetic }: {
  engine: Engine;
  onRun: () => void;
  busy: boolean;
  projectSynthetic: boolean;
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
              ? '🗺 Models the entire downstream river reach as a 2D shallow-water domain. Use for inundation extent, depth, velocity, and arrival time.'
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
              <div className="alert alert-warning" style={{ fontSize: 11, marginBottom: 0 }}>
                ⚠ Official laboratory example only. Requires switching to the synthetic laboratory project.
                Ujjani site runs are blocked until verified hydraulic inputs exist.
              </div>
              <button
                id={`btn-run-${engine.engine}`}
                className="btn btn-primary"
                disabled={busy || !projectSynthetic}
                onClick={onRun}
                title={!projectSynthetic ? 'Switch to synthetic laboratory project first' : undefined}
              >
                {busy ? <span className="spinner" /> : '▶'} Run Official Laboratory Example
              </button>
              {!projectSynthetic && (
                <p className="caption">Switch to the synthetic laboratory project to submit a run.</p>
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
  project, health, runs, onRefresh, onError, onNotice, onLoadResults, busy, setBusy,
}: SimulationProps) {
  const [engineChoice, setEngineChoice] = useState<'dualsphysics' | 'dflowfm'>('dualsphysics');

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

      {/* Synthetic project warning if needed */}
      {project && !isProjectSynthetic && (
        <div className="alert alert-warning" style={{ marginBottom: 20 }}>
          ⚠ The current project ({project.name}) is a <strong>site project</strong>.
          Laboratory examples require the synthetic laboratory project.
          Ujjani site runs are blocked until verified hydraulic boundary conditions exist.
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
