import React, { useState } from 'react';
import type { Dataset, Ensemble, Project, Scenario } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { NotImplementedBox } from '../components/StatusBadge';
import { createScenario, submitEnsemble } from '../api';

type ScenarioBuilderProps = {
  project: Project | null;
  datasets: Dataset[];
  scenarios: Scenario[];
  ensembles: Ensemble[];
  onRefresh: () => void;
  onError: (e: string) => void;
  onNotice: (n: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
};

type ScenarioType = 'breach' | 'release' | 'blockage';

const SCENARIO_TYPES = [
  {
    id: 'breach' as ScenarioType,
    name: 'Dam Breach',
    icon: '💥',
    desc: 'Hypothetical or computed dam failure scenario',
    implemented: true,
  },
  {
    id: 'release' as ScenarioType,
    name: 'Controlled Release',
    icon: '🚰',
    desc: 'Prescribed hydrograph from reservoir spillway',
    implemented: true,
  },
  {
    id: 'blockage' as ScenarioType,
    name: 'River Blockage',
    icon: '🪨',
    desc: 'Landslide dam or debris blockage scenario',
    implemented: false,
  },
];

const SENSITIVITY_PRESETS = [
  { id: 'slower', label: 'Coarse: 0.02 m', desc: 'Laboratory SPH particle-spacing sensitivity' },
  { id: 'reference', label: 'Reference: 0.01 m', desc: 'Laboratory SPH particle-spacing sensitivity' },
  { id: 'faster', label: 'Fine: 0.005 m', desc: 'Laboratory SPH particle-spacing sensitivity' },
];

export function ScenarioBuilder({
  project, datasets, scenarios, ensembles, onRefresh, onError, onNotice, busy, setBusy,
}: ScenarioBuilderProps) {
  const [scenarioType, setScenarioType] = useState<ScenarioType>('breach');
  const [scenarioName, setScenarioName] = useState('Hypothetical dam breach scenario');
  const [breachMode, setBreachMode] = useState<'computed_breach' | 'prescribed_release'>('computed_breach');
  const [hydrographId, setHydrographId] = useState('');
  const [startTime, setStartTime] = useState('2025-01-01T00:00:00+05:30');
  const [endTime, setEndTime] = useState('2025-01-02T00:00:00+05:30');
  const [datasetIds, setDatasetIds] = useState<string[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [ensembleName, setEnsembleName] = useState('Sensitivity ensemble');

  const hydroDatasets = datasets.filter((d) => d.kind === 'hydrology');

  async function handleSaveScenario() {
    if (!project) return;
    setBusy(true);
    try {
      const forcing =
        scenarioType === 'release'
          ? { mode: 'prescribed_release', historical: false, hydrograph_dataset_id: hydrographId || null }
          : { mode: 'computed_breach' };

      const body = {
        name: scenarioName,
        forcing,
        dataset_ids: [...new Set([...datasetIds, ...(scenarioType === 'release' && hydrographId ? [hydrographId] : [])])],
        start_time: startTime,
        end_time: endTime,
        time_step_seconds: 1,
        output_interval_seconds: 60,
        wet_threshold_m: 0.01,
        arrival_threshold_m: 0.1,
        initial_river_state: null,
        downstream_boundary: null,
        tributary_inflows: null,
        structure_treatment: null,
        roughness: null,
        assumptions: ['Scenario is hypothetical until evidence is verified'],
      };
      await createScenario(project.id, body);
      await onRefresh();
      onNotice('Scenario snapshot saved. Missing inputs remain visible in the audit.');
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitEnsemble() {
    if (!project) return;
    setBusy(true);
    try {
      const variants = [
        { engine: 'dualsphysics', case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: `ens-slow-${Date.now()}`, particle_spacing_m: 0.02 },
        { engine: 'dualsphysics', case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: `ens-ref-${Date.now()}`, particle_spacing_m: 0.01 },
        { engine: 'dualsphysics', case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: `ens-fast-${Date.now()}`, particle_spacing_m: 0.005 },
      ];
      await submitEnsemble(project.id, { name: ensembleName, variants });
      await onRefresh();
      onNotice('Sensitivity ensemble submitted. Requires synthetic laboratory project.');
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggleDataset(id: string) {
    setDatasetIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <div id="page-scenario-builder">
      <div className="page-header">
        <div className="page-eyebrow">③ Scenario Builder</div>
        <h1 className="page-title">Define Breach Scenario</h1>
        <p className="page-subtitle">
          Configure a dam failure or release scenario. Snapshot is immutable once saved.
          Unsupported scenario types are clearly labeled.
        </p>
      </div>

      {/* Scenario type selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">Scenario Type</span></div>
        <div className="card-body">
          <div className="scenario-type-grid">
            {SCENARIO_TYPES.map((type) => (
              <button
                key={type.id}
                id={`scenario-type-${type.id}`}
                className={`scenario-type-card${!type.implemented ? ' disabled' : scenarioType === type.id ? ' selected' : ''}`}
                onClick={() => type.implemented && setScenarioType(type.id)}
                disabled={!type.implemented}
              >
                <div className="scenario-type-icon">{type.icon}</div>
                <div className="scenario-type-name">{type.name}</div>
                <div className="scenario-type-desc">{type.desc}</div>
                {!type.implemented && (
                  <span className="badge badge-not-implemented" style={{ marginTop: 8 }}>NOT IMPLEMENTED</span>
                )}
              </button>
            ))}
          </div>
          {scenarioType === 'blockage' && (
            <NotImplementedBox feature="River blockage scenario" />
          )}
        </div>
      </div>

      {/* Scenario configuration */}
      {scenarioType !== 'blockage' && (
        <div className="two-col" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                {scenarioType === 'breach' ? 'Breach Parameters' : 'Release Parameters'}
              </span>
              <StatusBadge value="MIXED_ASSUMPTIONS" />
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Scenario Name</label>
                <input
                  id="scenario-name"
                  className="form-input"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Forcing Mode</label>
                <select
                  id="scenario-forcing-mode"
                  className="form-select"
                  value={breachMode}
                  onChange={(e) => { setBreachMode(e.target.value as typeof breachMode); setScenarioType(e.target.value === 'computed_breach' ? 'breach' : 'release'); }}
                >
                  <option value="computed_breach">computed_breach — Parameterised failure</option>
                  <option value="prescribed_release">prescribed_release — Given hydrograph</option>
                </select>
              </div>
              {breachMode === 'prescribed_release' && (
                <div className="form-group">
                  <label className="form-label">Hydrograph Dataset</label>
                  {hydroDatasets.length === 0 ? (
                    <div className="data-required-box">
                      <span className="badge badge-data-required">DATA REQUIRED</span>
                      <p style={{ fontSize: 12, marginTop: 6 }}>Upload a hydrology dataset in Data Setup first.</p>
                    </div>
                  ) : (
                    <select
                      id="scenario-hydrograph"
                      className="form-select"
                      value={hydrographId}
                      onChange={(e) => setHydrographId(e.target.value)}
                    >
                      <option value="">— None —</option>
                      {hydroDatasets.map((d) => (
                        <option key={d.id} value={d.id}>{d.name} (v{d.version})</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Start Time</label>
                  <input
                    id="scenario-start-time"
                    className="form-input"
                    type="text"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">End Time</label>
                  <input
                    id="scenario-end-time"
                    className="form-input"
                    type="text"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Dataset snapshot selector */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Include Datasets</span>
              <span style={{ fontSize: 12, color: '#64748B' }}>{datasetIds.length} selected</span>
            </div>
            <div className="card-body">
              {datasets.length === 0 ? (
                <div className="empty-state" style={{ padding: 20 }}>
                  <div className="empty-state-text">No datasets available. Upload in Data Setup first.</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {datasets.map((d) => (
                    <label
                      key={d.id}
                      style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13 }}
                    >
                      <input
                        type="checkbox"
                        checked={datasetIds.includes(d.id)}
                        onChange={() => toggleDataset(d.id)}
                        style={{ accentColor: '#F97316' }}
                      />
                      <span>{d.name}</span>
                      <StatusBadge value={d.provenance.status} />
                      <span style={{ fontSize: 11, color: '#94A3B8', marginLeft: 'auto' }}>{d.kind}</span>
                    </label>
                  ))}
                </div>
              )}
              <p className="caption" style={{ marginTop: 12 }}>
                Selected datasets are frozen into the scenario snapshot. Adding or updating datasets later requires a new scenario.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Save scenario */}
      {scenarioType !== 'blockage' && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
          <button
            id="btn-save-scenario"
            className="btn btn-primary"
            disabled={busy || !project || !scenarioName.trim()}
            onClick={handleSaveScenario}
          >
            {busy ? <span className="spinner" /> : '💾'} Save Scenario Snapshot
          </button>
        </div>
      )}

      {/* Sensitivity presets */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Sensitivity Presets</span>
          <span className="badge badge-gray">Ensemble</span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 16, lineHeight: 1.6 }}>
            Run three variants simultaneously to assess sensitivity to breach parameters.
            Requires the synthetic laboratory project (not the Ujjani site project).
          </p>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            {SENSITIVITY_PRESETS.map((p) => (
              <div key={p.id} className="card" style={{ flex: 1, minWidth: 140, padding: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{p.label}</div>
                <div style={{ fontSize: 11, color: '#64748B', marginTop: 4 }}>{p.desc}</div>
              </div>
            ))}
          </div>
          <div className="form-group">
            <label className="form-label">Ensemble Name</label>
            <input
              id="ensemble-name"
              className="form-input"
              value={ensembleName}
              onChange={(e) => setEnsembleName(e.target.value)}
              style={{ maxWidth: 360 }}
            />
          </div>
          <div className="alert alert-warning" style={{ marginBottom: 12 }}>
            ⚠ Sensitivity ensemble requires switching to the synthetic laboratory project.
            Ujjani site ensembles are blocked until verified hydraulic inputs exist.
          </div>
          <button
            id="btn-submit-ensemble"
            className="btn btn-outline-orange"
            disabled={busy || !project || !!project.synthetic === false}
            onClick={handleSubmitEnsemble}
          >
            Submit Sensitivity Ensemble
          </button>
          {!project?.synthetic && (
            <p className="caption" style={{ marginTop: 8 }}>
              Switch to the synthetic laboratory project to submit ensemble runs.
            </p>
          )}
        </div>
      </div>

      {/* Saved scenarios */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Saved Scenarios</span>
          <span style={{ fontSize: 12, color: '#64748B' }}>{scenarios.length} snapshots</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {scenarios.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">No scenarios saved</div>
              <div className="empty-state-text">Define and save a scenario to freeze inputs before simulation.</div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Evidence Mode</th>
                    <th>Forcing</th>
                    <th>Snapshot Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((s) => (
                    <tr key={s.id}>
                      <td>
                        {s.name}
                        <small><code>{s.id}</code></small>
                      </td>
                      <td><StatusBadge value={s.snapshot.input_mode} /></td>
                      <td>{s.snapshot.scenario?.forcing?.mode ?? '—'}</td>
                      <td><code style={{ fontSize: 10 }}>{s.sha256 ? `${s.sha256.slice(0, 16)}…` : 'Legacy record: checksum unavailable'}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Ensemble history */}
      {ensembles.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-header">
            <span className="card-title">Ensemble History</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Variants</th>
                    <th>Semantics</th>
                  </tr>
                </thead>
                <tbody>
                  {ensembles.map((e) => (
                    <tr key={e.id}>
                      <td>{e.name}<small><code>{e.id}</code></small></td>
                      <td><StatusBadge value={e.status} /></td>
                      <td>{e.run_ids.length}</td>
                      <td style={{ fontSize: 11, color: '#64748B' }}>{e.frequency_semantics}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
